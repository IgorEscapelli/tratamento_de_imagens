import os
import re
import shutil
import xml.etree.ElementTree as ET

# Pasta de entrada e saída
pasta_entrada = "imagens_originais"
pasta_saida = "imagens_sem_fundo"

# Apagar a pasta de saída se já existir
if os.path.exists(pasta_saida):
    shutil.rmtree(pasta_saida)

# Criar a pasta novamente
os.makedirs(pasta_saida)

NS_SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS_SVG)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

RE_UNIDADE = re.compile(r"^([0-9]*\.?[0-9]+)(px|pt|pc|mm|cm|in|em|ex|%)?$")
RE_NUMERO = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")

CORES_NOMEADAS = {
    "white": "#ffffff",
    "black": "#000000",
    "red": "#ff0000",
    "silver": "#c0c0c0",
    "gray": "#808080",
    "grey": "#808080",
    "maroon": "#800000",
    "yellow": "#ffff00",
    "olive": "#808000",
    "lime": "#00ff00",
    "green": "#008000",
    "aqua": "#00ffff",
    "teal": "#008080",
    "blue": "#0000ff",
    "navy": "#000080",
    "fuchsia": "#ff00ff",
    "purple": "#800080",
}


def converter_numero(valor):
    if valor is None:
        return None
    m = RE_UNIDADE.match(valor.strip())
    if m:
        return float(m.group(1))
    return None


def obter_cores(elemento):
    cores = []
    valor_fill = elemento.get("fill")
    if valor_fill:
        cores.append(valor_fill)
    estilo = elemento.get("style", "")
    for propriedade in estilo.split(";"):
        prop = propriedade.strip().lower()
        if prop.startswith("fill:"):
            cores.append(propriedade.split(":", 1)[1].strip().strip("'").strip('"'))
        elif prop.startswith("background-color:"):
            cores.append(propriedade.split(":", 1)[1].strip().strip("'").strip('"'))
    return [c for c in cores if c and c.lower() != "none"]


def normalizar_cor(cor):
    cor = cor.strip().lower()
    if cor in CORES_NOMEADAS:
        return CORES_NOMEADAS[cor]
    if re.fullmatch(r"#([0-9a-f]{3})", cor):
        return "#" + "".join(c * 2 for c in cor[1:])
    if re.fullmatch(r"#([0-9a-f]{6})", cor):
        return cor
    m = re.fullmatch(r"rgb\s*\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*(?:,\s*[0-9.]+\s*)?\)", cor)
    if m:
        return "#{:02x}{:02x}{:02x}".format(
            int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3)))
        )
    m = re.fullmatch(r"rgb\s*\(\s*([0-9.]+)%\s*,\s*([0-9.]+)%\s*,\s*([0-9.]+)%\s*\)", cor)
    if m:
        return "#{:02x}{:02x}{:02x}".format(
            int(float(m.group(1)) * 255 / 100),
            int(float(m.group(2)) * 255 / 100),
            int(float(m.group(3)) * 255 / 100),
        )
    return None


def definir_fill(elemento, valor):
    elemento.set("fill", valor)
    estilo = elemento.get("style", "")
    novas = []
    for propriedade in estilo.split(";"):
        if propriedade.strip().lower().startswith("fill:"):
            continue
        if propriedade.strip():
            novas.append(propriedade)
    elemento.set("style", ";".join(novas))


def bbox_do_caminho(d):
    # Calcula o retângulo envolvente (minx, miny, maxx, maxy) de um path.
    # Tolerante: nunca lança exceção, retorna None se não conseguir parsear.
    if not d:
        return None
    try:
        grupos = re.findall(r"[MmLlHhVvZzCcSsQqTtAa][-+0-9.eE]*", d)
        pontos = [(0.0, 0.0)]
        x = y = sx = sy = 0.0
        for grupo in grupos:
            cmd = grupo[0]
            nums = [float(t) for t in RE_NUMERO.findall(grupo[1:])]
            i = 0
            while i < len(nums):
                letra = cmd
                if letra in "Mm":
                    if i == 0:
                        nx = nums[0]
                        ny = nums[1] if len(nums) > 1 else 0.0
                        i += 2
                        if letra == "M":
                            x, y = nx, ny
                            sx, sy = x, y
                        else:
                            x += nx
                            y += ny
                        pontos.append((x, y))
                        continue
                    letra = "L" if letra == "M" else "l"
                if letra in "Ll":
                    if i + 1 >= len(nums):
                        break
                    if letra == "L":
                        x, y = nums[i], nums[i + 1]
                    else:
                        x += nums[i]
                        y += nums[i + 1]
                    i += 2
                    pontos.append((x, y))
                elif letra in "Hh":
                    if letra == "H":
                        x = nums[i]
                    else:
                        x += nums[i]
                    i += 1
                    pontos.append((x, y))
                elif letra in "Vv":
                    if letra == "V":
                        y = nums[i]
                    else:
                        y += nums[i]
                    i += 1
                    pontos.append((x, y))
                elif letra in "Zz":
                    x, y = sx, sy
                    pontos.append((x, y))
                    i = len(nums)
                elif letra in "CcSs":
                    i += 6
                elif letra in "QqTt":
                    i += 4
                elif letra in "Aa":
                    i += 7
        if not pontos:
            return None
        xs = [p[0] for p in pontos]
        ys = [p[1] for p in pontos]
        return min(xs), min(ys), max(xs), max(ys)
    except Exception:
        return None


def e_elemento_fundo(elemento, largura, altura):
    if not largura or not altura:
        return False
    etiqueta = elemento.tag.split("}")[-1]
    if etiqueta == "rect":
        x = converter_numero(elemento.get("x")) or 0
        y = converter_numero(elemento.get("y")) or 0
        w = converter_numero(elemento.get("width"))
        h = converter_numero(elemento.get("height"))
        if not w or not h:
            return False
        bbox = (x, y, x + w, y + h)
    elif etiqueta == "path":
        d = elemento.get("d")
        if not d:
            return False
        bbox = bbox_do_caminho(d)
        if not bbox or bbox[0] == bbox[2] or bbox[1] == bbox[3]:
            return False
    else:
        return False
    tol = max(1, min(largura, altura) * 0.01)
    x0, y0, x1, y1 = bbox
    return (
        abs(x0) <= 0.5
        and abs(y0) <= 0.5
        and abs(x1 - largura) <= tol
        and abs(y1 - altura) <= tol
    )


def remover_fundo_do_svg(caminho):
    arvore = ET.parse(caminho)
    raiz = arvore.getroot()
    etiqueta = raiz.tag.split("}")[-1]
    if etiqueta != "svg":
        raise ValueError(f"{os.path.basename(caminho)} não é um arquivo SVG válido")

    # Dimensões do canvas (viewBox tem prioridade)
    largura = None
    altura = None
    viewbox = raiz.get("viewBox")
    if viewbox:
        partes = viewbox.replace(",", " ").split()
        if len(partes) >= 4:
            largura = converter_numero(partes[2])
            altura = converter_numero(partes[3])
    if not largura:
        largura = converter_numero(raiz.get("width"))
    if not altura:
        altura = converter_numero(raiz.get("height"))

    # Mapa de pais (ElementTree padrão não tem getparent)
    pais = {filho: pai for pai in raiz.iter() for filho in pai}

    # Elementos que ocupam o canvas inteiro (fundo)
    elementos_fundo = []
    cor_fundo = None
    for elemento in raiz.iter():
        if not e_elemento_fundo(elemento, largura, altura):
            continue
        elementos_fundo.append(elemento)
        if cor_fundo is None:
            for c in obter_cores(elemento):
                normalizada = normalizar_cor(c)
                if normalizada:
                    cor_fundo = normalizada
                    break

    # Remover os elementos de fundo do canvas inteiro
    for elemento in elementos_fundo:
        pai = pais.get(elemento)
        if pai is not None:
            pai.remove(elemento)

    # Tornar transparentes os elementos com a cor de fundo
    if cor_fundo:
        for elemento in raiz.iter():
            for c in obter_cores(elemento):
                if normalizar_cor(c) == cor_fundo:
                    definir_fill(elemento, "none")
                    break

    # Limpar fundo declarado no elemento raiz
    estilo_raiz = raiz.get("style", "")
    novas = []
    for propriedade in estilo_raiz.split(";"):
        p = propriedade.strip().lower()
        if p.startswith("background") or p.startswith("fill:"):
            continue
        if propriedade.strip():
            novas.append(propriedade)
    raiz.set("style", ";".join(novas))
    raiz.attrib.pop("background", None)

    tem_image = bool(list(raiz.iter("{%s}image" % NS_SVG)))
    return arvore, cor_fundo, tem_image


for nome_arquivo in os.listdir(pasta_entrada):
    if not nome_arquivo.lower().endswith(".svg"):
        continue
    caminho_entrada = os.path.join(pasta_entrada, nome_arquivo)
    caminho_saida = os.path.join(pasta_saida, nome_arquivo)

    try:
        arvore, cor_fundo, tem_image = remover_fundo_do_svg(caminho_entrada)
        arvore.write(caminho_saida, encoding="utf-8", xml_declaration=True)
        mensagem = f"Fundo removido: {nome_arquivo}"
        if cor_fundo:
            mensagem += f" (cor de fundo: {cor_fundo})"
        else:
            mensagem += " (só retângulos full-canvas)"
        if tem_image:
            mensagem += " [AVISO: contém imagem embutida, verifique manualmente]"
        print(mensagem)
    except Exception as e:
        print(f"Erro ao processar {nome_arquivo}: {e}")

print("Concluído.")
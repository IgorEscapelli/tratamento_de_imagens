from PIL import Image
import os
import shutil

# Pasta de entrada e saída
pasta_entrada = "imagens_originais"
pasta_saida = "imagens_redimensionadas"

# Apagar a pasta de saída se já existir
if os.path.exists(pasta_saida):
    shutil.rmtree(pasta_saida)

# Criar a pasta novamente
os.makedirs(pasta_saida)

# Tamanho alvo (1000x1000) e margem interna
tamanho_desejado = (1000, 1000)
margem = 80

for nome_arquivo in os.listdir(pasta_entrada):
    if nome_arquivo.lower().endswith(('.jpg', '.jpeg', '.png')):
        caminho_entrada = os.path.join(pasta_entrada, nome_arquivo)
        caminho_saida = os.path.join(pasta_saida, nome_arquivo)

        try:
            with Image.open(caminho_entrada) as img:
                img = img.convert("RGBA")  # garantir canal alpha

                # Redimensionar proporcionalmente com margem
                max_largura = tamanho_desejado[0] - 2 * margem
                max_altura = tamanho_desejado[1] - 2 * margem
                img.thumbnail((max_largura, max_altura), Image.Resampling.LANCZOS)

                # Criar fundo branco
                fundo = Image.new("RGBA", tamanho_desejado, (255, 255, 255, 255))

                # Centralizar a imagem no fundo
                pos_x = (tamanho_desejado[0] - img.width) // 2
                pos_y = (tamanho_desejado[1] - img.height) // 2
                fundo.paste(img, (pos_x, pos_y), img)

                # Converter para RGB (sem transparência)
                imagem_final = fundo.convert("RGB")
                imagem_final.save(caminho_saida)

                print(f"Imagem redimensionada: {nome_arquivo}")
        except Exception as e:
            print(f"Erro ao processar {nome_arquivo}: {e}")

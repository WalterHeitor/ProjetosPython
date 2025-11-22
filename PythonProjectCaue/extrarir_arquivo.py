import os
import zipfile
import shutil

# Caminho da pasta onde estão os arquivos ZIP
PASTA_ZIP = r"W:\CAUE\lucastylty_pr\michel_bastos_ze_roberto"

def gerar_nome_unico(destino, nome_arquivo):
    """
    Gera um nome único caso já exista um arquivo com o mesmo nome.
    """
    base, ext = os.path.splitext(nome_arquivo)
    contador = 1
    novo_nome = nome_arquivo
    while os.path.exists(os.path.join(destino, novo_nome)):
        novo_nome = f"{base}_{contador}{ext}"
        contador += 1
    return novo_nome

def extrair_videos_mp4(pasta_zip, pasta_destino):
    """
    Extrai apenas arquivos .mp4 dos arquivos ZIP e os move para a pasta raiz.
    """
    for arquivo in os.listdir(pasta_zip):
        if arquivo.lower().endswith(".zip"):
            caminho_zip = os.path.join(pasta_zip, arquivo)
            print(f"🔄 Extraindo vídeos de: {arquivo}")

            try:
                with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
                    for item in zip_ref.namelist():
                        if item.lower().endswith(".mp4"):
                            nome_arquivo = os.path.basename(item)
                            if not nome_arquivo:
                                continue

                            # Garante nome único para evitar sobrescrever
                            nome_unico = gerar_nome_unico(pasta_destino, nome_arquivo)

                            # Extrai temporariamente
                            temp_path = zip_ref.extract(item, pasta_destino)

                            # Move para a pasta raiz com nome único
                            destino_final = os.path.join(pasta_destino, nome_unico)
                            shutil.move(temp_path, destino_final)

                            print(f"✅ Extraído: {nome_unico}")
            except Exception as e:
                print(f"❌ Erro ao processar {arquivo}: {e}")

def main():
    """
    Função principal que executa a extração dos vídeos.
    """
    print("🚀 Iniciando extração dos vídeos .mp4...\n")
    extrair_videos_mp4(PASTA_ZIP, PASTA_ZIP)
    print("\n🎉 Finalizado! Todos os arquivos .mp4 foram movidos para:")
    print(PASTA_ZIP)

if __name__ == "__main__":
    main()

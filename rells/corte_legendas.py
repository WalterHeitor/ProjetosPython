import os
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.config import change_settings

# Configurar o caminho do ImageMagick
change_settings({
    "IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
})

def adicionar_legendas_duas_fases(video, largura, altura, duracao_parte):
    margem_horizontal = 40
    posicao_vertical = altura * 0.55
    metade = duracao_parte / 2

    # Legenda inferior fixa
    texto_inferior = "#g4educacao\n@g4educacao @tallisgomes @alfredosoares @bruno.nardon"
    legenda_inferior = TextClip(
        texto_inferior,
        fontsize=38,
        color='white',
        font="Arial",
        method='caption',
        size=(largura - margem_horizontal * 2, None)
    ).set_duration(duracao_parte).set_position(("center", altura - 150))

    # Versículo 1
    texto_topo_1 = 'Êxodo 20:9:\n"Seis dias trabalharás, e farás toda a tua obra."'
    versiculo_1 = TextClip(
        texto_topo_1,
        fontsize=36,
        color='white',
        font="Arial",
        method='caption',
        size=(largura - margem_horizontal * 2, None)
    ).set_duration(metade).set_position(("center", posicao_vertical))

    # Versículo 2
    texto_topo_2 = 'Provérbios 10:4:\n"A mão preguiçosa empobrece, mas a mão dos diligentes enriquece"'
    versiculo_2 = TextClip(
        texto_topo_2,
        fontsize=36,
        color='white',
        font="Arial",
        method='caption',
        size=(largura - margem_horizontal * 2, None)
    ).set_start(metade).set_duration(metade).set_position(("center", posicao_vertical))

    # Compor vídeo com todos os elementos
    return CompositeVideoClip([video, legenda_inferior, versiculo_1, versiculo_2])

def dividir_em_sete_partes_com_legendas(caminho_entrada, caminho_saida_base):
    video = VideoFileClip(caminho_entrada)
    duracao_total = video.duration
    duracao_parte = duracao_total / 7

    for i in range(7):
        inicio = i * duracao_parte
        fim = inicio + duracao_parte

        subclip = video.subclip(inicio, fim)
        largura, altura = subclip.size

        # Adiciona legenda com os dois versículos
        video_legendas = adicionar_legendas_duas_fases(subclip, largura, altura, duracao_parte)

        caminho_saida = f"{caminho_saida_base}_parte_{i+1}.mp4"
        print(f"Exportando: {caminho_saida}")
        video_legendas.write_videofile(
            caminho_saida,
            codec="libx264",
            audio_codec="aac"
        )

if __name__ == "__main__":
    caminho_entrada = r"D:\Fabrica de cortes\G4\conteudo\corte1.mp4"
    caminho_saida_base = r"D:\Fabrica de cortes\G4\conteudosFormatados\video"

    dividir_em_sete_partes_com_legendas(caminho_entrada, caminho_saida_base)
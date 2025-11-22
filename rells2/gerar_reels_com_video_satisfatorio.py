from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ImageClip
from moviepy.config import change_settings
from moviepy.video.fx.fadein import fadein
from PIL import Image
import os

# Compatibilidade com Pillow
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Caminho do ImageMagick (ajuste se precisar)
change_settings({
    "IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
})

def gerar_reels_com_video_satisfatorio(video_path, video_satisfatorio_path, srt_path, pasta_saida,
                                       largura=960, altura=540, fonte='Arial-Bold'):

    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)

    video = VideoFileClip(video_path)
    video_satis = VideoFileClip(video_satisfatorio_path)

    banner_transparente = r"D:\Fabrica de cortes\G4\alfredo\banner_rasgado_transparente.png"
    marca_dagua_path = r"D:\Fabrica de cortes\G4\alfredo\ulfrlobo.png"

    with open(srt_path, encoding='utf-8') as f:
        conteudo = f.read().strip().split("\n\n")

    largura_total = largura * 2  # vídeo final terá largura dupla
    total_blocos = len(conteudo)
    limite_satisfatorio = total_blocos // 3  # usar satisfatório só até esse índice

    for i, bloco in enumerate(conteudo):
        linhas = bloco.strip().split("\n")
        if len(linhas) < 3:
            continue

        tempo = linhas[1]
        texto = linhas[2]

        try:
            inicio_str, _ = tempo.split(" --> ")
            h, m, s_ms = inicio_str.split(":")
            s, ms = s_ms.split(',')

            inicio = int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000

            fim = inicio + 15
            fim = min(fim, video.duration, video_satis.duration)

            # Trecho esquerdo: sempre do vídeo principal
            trecho = video.subclip(inicio, fim).resize(height=altura).crop(x2=largura)

            # Trecho direito: satisfatório no primeiro terço, senão o mesmo do vídeo principal
            if i < limite_satisfatorio:
                trecho_satis = video_satis.subclip(inicio, fim).resize(height=altura).crop(x2=largura)
            else:
                trecho_satis = video.subclip(inicio, fim).resize(height=altura).crop(x2=largura)

            trecho = trecho.set_position(("left", "center"))
            trecho_satis = trecho_satis.set_position((largura, "center"))

            # Texto legenda
            texto_legenda = TextClip(
                txt=texto,
                fontsize=24,
                font=fonte,
                color='yellow',
                method='caption',
                size=(largura - 40, None),
                align='center',
                stroke_color='black',
                stroke_width=1
            ).set_duration(trecho.duration).fx(fadein, 0.5)

            pos_x_texto = largura + 20
            pos_y_texto = (altura - texto_legenda.h) / 2
            texto_legenda = texto_legenda.set_position((pos_x_texto, pos_y_texto))

            # Banner e marca d'água
            banner = (ImageClip(banner_transparente)
                      .resize(width=int(largura * 0.6))
                      .set_duration(trecho.duration))
            altura_banner = banner.h
            pos_y_banner = altura - altura_banner - 20
            banner = banner.set_position(("center", pos_y_banner))

            marca_dagua = (ImageClip(marca_dagua_path)
                           .resize(height=60)
                           .set_duration(trecho.duration)
                           .set_position('center')
                           .set_opacity(0.6))

            # Mensagem final
            dur_final = 2
            mensagem_final = (TextClip(
                "Gostou? Então curte e compartilha! 💥",
                fontsize=28,
                font=fonte,
                color='white',
                method='caption',
                size=(largura, None),
                align='center'
            )
            .set_duration(dur_final)
            .set_position((pos_x_texto, pos_y_texto))
            .crossfadein(0.3)
            .set_start(trecho.duration - dur_final))

            # Composição final
            final = CompositeVideoClip(
                [trecho, trecho_satis, texto_legenda, banner, marca_dagua, mensagem_final],
                size=(largura_total, altura)
            )

            nome_arquivo = os.path.join(pasta_saida, f"reel_{i+1:02}.mp4")
            final.write_videofile(
                nome_arquivo,
                codec="libx264",
                audio_codec="aac",
                preset="fast",
                threads=4,
                fps=30,
                ffmpeg_params=["-movflags", "+faststart"]
            )

        except Exception as e:
            print(f"❌ Erro no bloco {i+1}: {e}")

    print("✅ Todos os Reels foram gerados com sucesso!")

if __name__ == "__main__":
    video = r"D:\Fabrica de cortes\brasil_paralelo\video.mp4"
    video_satisfatorio = r"D:\Fabrica de cortes\satisfatorio\foqueira.mp4"
    srt = r"D:\Fabrica de cortes\brasil_paralelo\legenda_combinada_para_reels.srt"
    saida = r"D:\Fabrica de cortes\brasil_paralelo\reels_final_satisfatorio"

    gerar_reels_com_video_satisfatorio(video, video_satisfatorio, srt, saida)

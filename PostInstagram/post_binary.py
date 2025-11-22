import datetime
import sys
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import traceback
import os

# ===============================
# CONFIGURAÇÃO DE EXPIRAÇÃO
# ===============================
EXPIRATION_DATE = datetime.date(2025, 9, 30)  # Ano, Mês, Dia

if datetime.date.today() > EXPIRATION_DATE:
    print("❌ Este programa expirou. Contate o administrador.")
    sys.exit(1)

# ===============================
# CONFIGURAÇÕES
# ===============================
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'n8n',
    'user': 'n8n',
    'password': 'n8npass'
}

VIDEO_BASE_PATH = r"W:\docker\videos"

# ===============================
# INPUTS DO USUÁRIO
# ===============================
INSTAGRAM_USER_ID = input("Digite o ID do Instagram: ").strip()
ACCESS_TOKEN = input("Digite o Access Token do Instagram: ").strip()
num_videos = int(input("Quantos vídeos deseja postar? "))
interval_post = int(input("Intervalo em segundos entre cada vídeo: "))

# ===============================
# FUNÇÕES BASE
# ===============================
def get_next_pending_video():
    print("🔎 Consultando próximo vídeo pendente no banco...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT id, nome_arquivo, legenda AS caption
            FROM reels_janguile_diniz
            WHERE status = 'pendente'
            ORDER BY id ASC
            LIMIT 1;
        """)

        video = cur.fetchone()
        cur.close()
        conn.close()

        if video:
            # Monta caminho completo do vídeo
            video_path = os.path.join(VIDEO_BASE_PATH, video['nome_arquivo'].lstrip("/").replace('/', os.sep))
            if not os.path.isfile(video_path):
                print(f"❌ Arquivo não encontrado: {video_path}")
                return None
            video['path'] = video_path
            print(f"✅ Encontrado vídeo ID {video['id']}: {video_path}")
        else:
            print("⚠️ Nenhum vídeo pendente encontrado.")
        return video
    except Exception as e:
        print("❌ Erro ao consultar banco de dados:", e)
        traceback.print_exc()
        return None


def create_instagram_media_binary(video_path, caption):
    print("📤 Criando mídia no Instagram via upload binário...")
    try:
        # API Instagram Graph
        url_create = f'https://graph.instagram.com/v22.0/{INSTAGRAM_USER_ID}/media'

        with open(video_path, 'rb') as f:
            video_data = f.read()

        payload = {
            'access_token': ACCESS_TOKEN,
            'media_type': 'REELS',
            'caption': caption
        }

        files = {
            'video_file': ('video.mp4', video_data, 'video/mp4')
        }

        r = requests.post(url_create, data=payload, files=files)
        r.raise_for_status()
        creation_id = r.json()['id']
        print(f"🆔 Mídia criada com ID {creation_id}")
        return creation_id
    except Exception as e:
        print("❌ Erro ao criar mídia binária:", e)
        traceback.print_exc()
        return None


def check_media_status(creation_id):
    print(f"⏳ Verificando status da mídia {creation_id}...")
    try:
        url_status = f'https://graph.instagram.com/v22.0/{creation_id}?fields=status_code&access_token={ACCESS_TOKEN}'
        while True:
            r = requests.get(url_status)
            r.raise_for_status()
            status = r.json().get('status_code')
            print(f"🔄 Status atual: {status}")
            if status == 'FINISHED':
                print("✅ Mídia pronta para publicação!")
                break
            elif status == 'ERROR':
                print("❌ Ocorreu um erro no processamento do vídeo no Instagram!")
                break
            time.sleep(60)
    except Exception as e:
        print("❌ Erro ao checar status:", e)
        traceback.print_exc()


def publish_instagram_media(creation_id):
    print(f"🚀 Publicando mídia {creation_id} no Instagram...")
    try:
        url_publish = f'https://graph.instagram.com/v23.0/{INSTAGRAM_USER_ID}/media_publish'
        payload_publish = {
            'creation_id': creation_id,
            'access_token': ACCESS_TOKEN
        }
        r = requests.post(url_publish, data=payload_publish)
        r.raise_for_status()
        print("🎉 Mídia publicada com sucesso!")
        return r.json()
    except Exception as e:
        print("❌ Erro ao publicar mídia:", e)
        traceback.print_exc()


def update_video_status(video_id):
    print(f"💾 Atualizando status do vídeo {video_id} no banco para 'postado'...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            UPDATE reels_janguile_diniz
            SET status = 'postado', data_postagem = NOW()
            WHERE id = %s;
        """, (video_id,))
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Status atualizado no banco.")
    except Exception as e:
        print("❌ Erro ao atualizar status no banco:", e)
        traceback.print_exc()


# ===============================
# MAIN LOOP PARA MÚLTIPLOS VÍDEOS
# ===============================
def main():
    for i in range(num_videos):
        print(f"\n🎬 Postando vídeo {i+1}/{num_videos}...")
        try:
            video = get_next_pending_video()
            if not video:
                print("⏭ Nada para postar no momento.")
                break

            creation_id = create_instagram_media_binary(video['path'], video['caption'])
            if not creation_id:
                print("❌ Falha na criação da mídia. Abortando este vídeo.")
                continue

            check_media_status(creation_id)
            publish_instagram_media(creation_id)
            update_video_status(video['id'])

        except Exception as e:
            print("❌ Erro inesperado no fluxo principal:", e)
            traceback.print_exc()

        print(f"⏳ Aguardando {interval_post} segundos até o próximo vídeo...")
        time.sleep(interval_post)

    print("✅ Fluxo concluído para todos os vídeos!")


if __name__ == "__main__":
    main()

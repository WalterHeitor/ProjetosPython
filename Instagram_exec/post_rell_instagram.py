import datetime
import sys
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import traceback

# ===============================
# CONFIGURAÇÃO DE EXPIRAÇÃO
# ===============================
EXPIRATION_DATE = datetime.date(2025, 12, 31)  # Ano, Mês, Dia

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

CLOUD_FLARE_FILE = r"W:\docker\videos\cloudflare_url.txt"

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
def get_cloudflare_base_url():
    try:
        with open(CLOUD_FLARE_FILE, "r", encoding="utf-8") as f:
            base_url = f.read().strip().replace('\ufeff','')  # remove BOM
        print("🌐 Base URL Cloudflare:", base_url)
        return base_url
    except Exception as e:
        print("❌ Erro ao ler Cloudflare URL:", e)
        traceback.print_exc()
        return None


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
            base_url = get_cloudflare_base_url()
            if not base_url:
                return None
            video['url_publica'] = f"{base_url.rstrip('/')}/{video['nome_arquivo'].lstrip('/')}"
            print(f"✅ Encontrado vídeo ID {video['id']}: {video['url_publica']}")
        else:
            print("⚠️ Nenhum vídeo pendente encontrado.")
        return video
    except Exception as e:
        print("❌ Erro ao consultar banco de dados:", e)
        traceback.print_exc()
        return None


def create_instagram_media(video_url, caption):
    print("📤 Criando mídia no Instagram...")
    try:
        url_create = f'https://graph.instagram.com/v22.0/{INSTAGRAM_USER_ID}/media'
        payload = {
            'video_url': video_url,
            'caption': caption,
            'media_type': 'REELS',
            'access_token': ACCESS_TOKEN
        }
        r = requests.post(url_create, data=payload)
        r.raise_for_status()
        creation_id = r.json()['id']
        print(f"🆔 Mídia criada com ID {creation_id}")
        return creation_id
    except Exception as e:
        print("❌ Erro ao criar mídia:", e)
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

            creation_id = create_instagram_media(video['url_publica'], video['caption'])
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

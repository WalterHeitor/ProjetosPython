import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import traceback  # <-- Importante para capturar a stacktrace

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

INSTAGRAM_USER_ID = '17841475199270641'
ACCESS_TOKEN = 'IGAAQqHFTdCEhBZAFBRQ0FRckJIX0hHUEM0UjRnemN6RlNjOENuOS1rYlpXSkhHRlB0MXptTTQ5WEY2cTdKRGJhOHNiRzVUdWt5a1NlLTdKby1ZAcHpBRnRTUUc4eU9uNlNTZAWdHUV9zRTg5OHJDZAmV2d1ZAmM1Q5eXphSHZAkMHRCYwZDZD'
CHECK_INTERVAL = 60
CLOUD_FLARE_FILE = r"W:\docker\videos\cloudflare_url.txt"

# ===============================
# FUNÇÕES
# ===============================
def get_cloudflare_base_url():
    try:
        with open(CLOUD_FLARE_FILE, "r", encoding="utf-8") as f:
            base_url = f.read().strip().replace('\ufeff','')
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
            FROM reels_cortesfut_ma1
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
    except requests.exceptions.HTTPError as e:
        print("❌ Erro HTTP ao criar mídia:", e.response.text)
        traceback.print_exc()
        return None
    except Exception as e:
        print("❌ Erro inesperado ao criar mídia:", e)
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
            time.sleep(CHECK_INTERVAL)
    except requests.exceptions.HTTPError as e:
        print("❌ Erro HTTP ao checar status:", e.response.text)
        traceback.print_exc()
    except Exception as e:
        print("❌ Erro inesperado ao checar status:", e)
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
    except requests.exceptions.HTTPError as e:
        print("❌ Erro HTTP ao publicar mídia:", e.response.text)
        traceback.print_exc()
    except Exception as e:
        print("❌ Erro inesperado ao publicar mídia:", e)
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
# MAIN
# ===============================
def main():
    try:
        video = get_next_pending_video()
        if not video:
            print("⏭ Nada para postar no momento.")
            return

        creation_id = create_instagram_media(video['url_publica'], video['caption'])
        if not creation_id:
            print("❌ Falha na criação da mídia. Abortando fluxo.")
            return

        check_media_status(creation_id)
        publish_instagram_media(creation_id)
        update_video_status(video['id'])
        print("🎬 Fluxo concluído com sucesso!")
    except Exception as e:
        print("❌ Erro crítico no fluxo principal:", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()

import datetime
import sys
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import traceback
import subprocess
import os

# ===============================
# CONFIGURAÇÃO DE EXPIRAÇÃO
# ===============================
EXPIRATION_DATE = datetime.date(2025, 9, 30)
if datetime.date.today() > EXPIRATION_DATE:
    print("❌ Este programa expirou. Contate o administrador.")
    sys.exit(1)

# ===============================
# INPUTS DO USUÁRIO
# ===============================
INSTAGRAM_USER_ID = input("Digite o ID do Instagram: ").strip()
ACCESS_TOKEN = input("Digite o Access Token do Instagram: ").strip()
TABLE_NAME = input("Digite o nome da tabela no banco: ").strip()
num_videos = int(input("Quantos vídeos deseja postar? "))
interval_post = int(input("Intervalo em segundos entre cada vídeo: "))

# ===============================
# CONFIGURAÇÕES DO BANCO
# ===============================
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'n8n',
    'user': 'n8n',
    'password': 'n8npass'
}

# ===============================
# PATHS
# ===============================
PROJECT_ROOT = os.getcwd()
DOCKER_VIDEOS_DIR = os.path.join(PROJECT_ROOT, "videos", TABLE_NAME)
CLOUD_FLARE_DIR = os.path.join(PROJECT_ROOT, "cloudflare")
CLOUD_FLARE_FILE = os.path.join(CLOUD_FLARE_DIR, "cloudflare_url.txt")

# Garantir que a pasta cloudflare exista
os.makedirs(CLOUD_FLARE_DIR, exist_ok=True)

# ===============================
# FUNÇÕES DE DOCKER
# ===============================
def start_docker():
    print("🚀 Subindo containers...")
    if os.path.exists(CLOUD_FLARE_FILE):
        os.remove(CLOUD_FLARE_FILE)  # remove apenas o arquivo antigo
    subprocess.run(["docker-compose", "up", "-d"], check=True)
    print("✅ Containers subiram!")

def stop_docker():
    print("🛑 Encerrando containers...")
    subprocess.run(["docker-compose", "down"], check=True)
    print("✅ Containers encerrados!")

def esperar_banco():
    print("⏳ Aguardando banco de dados...")
    for _ in range(30):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.close()
            print("✅ Banco de dados pronto!")
            return
        except psycopg2.OperationalError:
            time.sleep(2)
    print("❌ Banco não respondeu a tempo!")
    stop_docker()
    sys.exit(1)

# ===============================
# FUNÇÕES CLOUD FLARE
# ===============================
def wait_for_cloudflare_url(timeout=60):
    """Aguarda o arquivo cloudflare_url.txt ser gerado pelo container com URL válida"""
    waited = 0
    print("⏳ Aguardando Cloudflare gerar URL...")
    while waited < timeout:
        if os.path.exists(CLOUD_FLARE_FILE):
            with open(CLOUD_FLARE_FILE, "r", encoding="utf-8") as f:
                base_url = f.read().strip().replace('\ufeff', '')
                if base_url:
                    print("✅ Cloudflare URL pronta:", base_url)
                    return base_url
        time.sleep(2)
        waited += 2
    raise FileNotFoundError(f"❌ Cloudflare URL não gerada após {timeout}s")

def check_url_accessible(url, timeout=10):
    """Verifica se a URL do vídeo está acessível antes de enviar ao Instagram"""
    try:
        r = requests.head(url, timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False

def wait_video_accessible(video_url, timeout=300, interval=10):
    """
    Espera até que a URL do vídeo esteja acessível.
    timeout: tempo máximo total em segundos
    interval: intervalo entre tentativas em segundos
    """
    waited = 0
    print(f"⏳ Verificando se o vídeo está acessível: {video_url}")
    while waited < timeout:
        if check_url_accessible(video_url):
            print("✅ Vídeo acessível!")
            return True
        print(f"⚠️ Vídeo ainda não acessível, aguardando {interval} segundos...")
        time.sleep(interval)
        waited += interval
    print("❌ Tempo limite atingido, vídeo não acessível.")
    return False

# ===============================
# FUNÇÕES INSTAGRAM
# ===============================
def get_next_pending_video(base_url):
    print("🔎 Consultando próximo vídeo pendente no banco...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(f"""
            SELECT id, nome_arquivo, legenda AS caption
            FROM "{TABLE_NAME}"
            WHERE status = 'pendente'
            ORDER BY id ASC
            LIMIT 1;
        """)
        video = cur.fetchone()
        cur.close()
        conn.close()

        if video:
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
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print("❌ HTTP Error ao criar mídia!")
            print("Status Code:", r.status_code)
            print("Response:", r.text)
            return None

        response_json = r.json()
        if 'id' not in response_json:
            print("❌ Erro: campo 'id' não retornado na resposta")
            print("Response JSON:", response_json)
            return None

        creation_id = response_json['id']
        print(f"🆔 Mídia criada com ID {creation_id}")
        return creation_id

    except requests.RequestException as e:
        print("❌ Erro de request:", e)
        traceback.print_exc()
        return None
    except Exception as e:
        print("❌ Erro inesperado:", e)
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
        try:
            r.raise_for_status()
        except requests.HTTPError:
            print("❌ HTTP Error ao publicar mídia!")
            print("Status Code:", r.status_code)
            print("Response:", r.text)
            return None

        print("🎉 Mídia publicada com sucesso!")
        return r.json()
    except requests.RequestException as e:
        print("❌ Erro de request:", e)
        traceback.print_exc()
    except Exception as e:
        print("❌ Erro inesperado:", e)
        traceback.print_exc()

def update_video_status(video_id):
    print(f"💾 Atualizando status do vídeo {video_id} no banco para 'postado'...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE "{TABLE_NAME}"
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
# MAIN LOOP
# ===============================
def main():
    try:
        start_docker()
        esperar_banco()
        base_url = wait_for_cloudflare_url()

        for i in range(num_videos):
            print(f"\n🎬 Postando vídeo {i+1}/{num_videos}...")
            video = get_next_pending_video(base_url)
            if not video:
                print("⏭ Nada para postar no momento.")
                break

            # Espera até o vídeo ficar acessível
            if not wait_video_accessible(video['url_publica'], timeout=300, interval=10):
                print("❌ Não foi possível acessar o vídeo, pulando...")
                continue

            creation_id = create_instagram_media(video['url_publica'], video['caption'])
            if not creation_id:
                print("❌ Falha na criação da mídia. Abortando este vídeo.")
                continue

            check_media_status(creation_id)
            publish_instagram_media(creation_id)
            update_video_status(video['id'])

            print(f"⏳ Aguardando {interval_post} segundos até o próximo vídeo...")
            time.sleep(interval_post)

        print("✅ Fluxo concluído para todos os vídeos!")

    finally:
        stop_docker()

if __name__ == "__main__":
    main()

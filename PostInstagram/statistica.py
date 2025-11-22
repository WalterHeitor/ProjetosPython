import requests
from datetime import datetime, timedelta

# -----------------------------
# CONFIGURAÇÃO
# -----------------------------
#corte_captao
# ACCESS_TOKEN = "IGAAJZCkjZA22WVBZAFA2MWJuWVdiU0JueWh4U3FEMkY3LUJPVlFsSzJHci1rVV9yY01OeHdfOTkyQlhVaGdEQ0lqSUpnbXE4ekM1dWJ6WmxZAaVVSaHE1S2FSN3UzQzNGSThQNnRJQVREMXhrSkMwYXROSXRMRkVxbnVINHN1cnZAPUQZDZD"
# IG_USER_ID = "17841475306560770"
# snipe da bola
ACCESS_TOKEN ="IGAAJZCkjZA22WVBZAFA3dzVUZAXNvOWFMLXJWSTVqcTJXcTQ3ZA21lR2FHSnJKcVhTNV9SMzJSeXF2c1JWQjNQUFJqemctV2pNMXZAYRHBIbXE2Q1BOWVV1YjlWQTFHbWVrNjktWmszZAE94YWx6QUpDMEpjWWkxQk5hRkYwWm1NWmlWTQZDZD"
IG_USER_ID = "17841475390049253"

DATA_INICIAL = datetime.utcnow() - timedelta(days=1)  # últimas 24 horas (UTC)

# DATA_INICIAL = datetime(2025, 8, 1)  # Data inicial para filtrar vídeos

# -----------------------------
# FUNÇÕES
# -----------------------------
def pegar_midias(ig_user_id, access_token):
    """Pega todas as mídias do usuário, seguindo a paginação"""
    todas_midias = []
    url = f"https://graph.instagram.com/v22.0/{ig_user_id}/media"
    params = {
        "fields": "id,media_type,timestamp,caption",
        "access_token": access_token
    }

    while url:
        response = requests.get(url, params=params).json()
        midias = response.get("data", [])
        todas_midias.extend(midias)
        # Próxima página, se existir
        url = response.get("paging", {}).get("next")
        params = None  # depois da primeira página, o link já contém os parâmetros

    return todas_midias

def filtrar_videos_desde(midias, data_inicial):
    """Filtra apenas vídeos a partir da data inicial"""
    videos = [
        post for post in midias
        if post['media_type'] == 'VIDEO' and datetime.fromisoformat(post['timestamp'][:-5]) >= data_inicial
    ]
    return videos

def pegar_estatisticas(media_id, access_token):
    """Pega estatísticas básicas de cada vídeo"""
    url = f"https://graph.instagram.com/v22.0/{media_id}/insights"
    params = {
        "metric": "impressions,reach,engagement,video_views",
        "access_token": access_token
    }
    response = requests.get(url, params=params).json()
    return response.get("data", [])

# -----------------------------
# MAIN
# -----------------------------
def main():
    # 1️⃣ Pegar todas as mídias
    midias = pegar_midias(IG_USER_ID, ACCESS_TOKEN)
    print(f"Total de mídias encontradas: {len(midias)}")

    # 2️⃣ Filtrar apenas vídeos desde a DATA_INICIAL
    videos = filtrar_videos_desde(midias, DATA_INICIAL)
    print(f"Total de vídeos desde {DATA_INICIAL.date()}: {len(videos)}\n")

    # # 3️⃣ Mostrar estatísticas de cada vídeo
    # for i, video in enumerate(videos, 1):
    #     print(f"Vídeo {i}: ID {video['id']} - Publicado em {video['timestamp']}")
    #     stats = pegar_estatisticas(video['id'], ACCESS_TOKEN)
    #     for s in stats:
    #         print(f"  {s['name']}: {s['values'][0]['value']}")
    #     print("-" * 30)

if __name__ == "__main__":
    main()

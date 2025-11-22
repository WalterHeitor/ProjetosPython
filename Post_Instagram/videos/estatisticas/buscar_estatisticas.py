

import os
import requests
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
import traceback
from dateutil import parser
from openpyxl import load_workbook
from openpyxl.chart import BarChart, Reference

# ================================
# CONFIGURAÇÕES INICIAIS
# ================================
load_dotenv()
ACCESS_TOKEN = "IGAAJZCkjZA22WVBZAE9DVWpvU0lIY1JJYmRwWWpzOGtPUy1BUlBNV0MtS1d3MEZABTHhDOWllY1paVWtUVmJkdWxUSkdiUTFqS0tLSHgtZAURheXBrRFpNaGp5cDFMZAVB6Vzh0TUloT1JERTdGZAElhUkVzNHY4YUFGdGM5SVR2TVU3dwZDZD"
INSTAGRAM_USER_ID = "17841475390049253"

HASHTAG = "#lucastylty"
API_URL = "https://graph.instagram.com/v23.0"

# Período do ranking
START_DATE = datetime(datetime.now().year, datetime.now().month, 1, tzinfo=timezone.utc)
TODAY = datetime.now(timezone.utc)

# Pasta para salvar Excel
OUTPUT_DIR = r"W:\docker\relatorios"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ================================
# FUNÇÕES
# ================================
def safe_request(url, params=None):
    """Faz requisição GET e captura erros."""
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"❌ Erro na requisição para {url}: {e}")
        traceback.print_exc()
        return None

def get_all_posts():
    """Busca todos os posts da conta Instagram."""
    url = f"{API_URL}/{INSTAGRAM_USER_ID}/media"
    params = {
        "fields": "id,caption,media_type,media_url,like_count,comments_count,timestamp",
        "access_token": ACCESS_TOKEN,
        "limit": 100
    }
    data = safe_request(url, params)
    return data.get("data", []) if data else []

def filter_posts(posts):
    """Filtra posts com #tylty e dentro do período."""
    filtered = []
    for post in posts:
        try:
            caption = post.get("caption", "").lower()
            timestamp = parser.isoparse(post['timestamp'])  # offset-aware
            if HASHTAG.lower() in caption and START_DATE <= timestamp <= TODAY:
                filtered.append(post)
        except Exception as e:
            print(f"⚠️ Erro ao processar post {post.get('id')}: {e}")
            traceback.print_exc()
    return filtered

def generate_ranking(posts):
    """Cria DataFrame ordenado pelo engajamento."""
    df = pd.DataFrame(posts)
    if df.empty:
        return df
    df['views'] = df['like_count'] + df['comments_count']
    df['timestamp'] = df['timestamp'].apply(lambda x: parser.isoparse(x).strftime("%Y-%m-%d %H:%M:%S"))
    df = df.sort_values(by="views", ascending=False).reset_index(drop=True)
    return df

def save_to_excel(df):
    """Salva ranking em Excel e cria gráfico de barras."""
    try:
        filename = os.path.join(OUTPUT_DIR, f"ranking_{HASHTAG[1:]}_{TODAY.strftime('%Y%m%d')}.xlsx")
        df.to_excel(filename, index=False)

        # Criar gráfico
        wb = load_workbook(filename)
        ws = wb.active

        chart = BarChart()
        chart.title = f"Engajamento #tylty ({TODAY.strftime('%Y-%m-%d')})"
        chart.y_axis.title = 'Views (Likes + Comentários)'
        chart.x_axis.title = 'Posts'

        data = Reference(ws, min_col=8, min_row=1, max_row=len(df)+1)  # coluna 'views'
        cats = Reference(ws, min_col=2, min_row=2, max_row=len(df)+1)   # coluna 'caption'
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)

        ws.add_chart(chart, "J2")

        wb.save(filename)
        return filename
    except Exception as e:
        print(f"❌ Erro ao salvar Excel ou criar gráfico: {e}")
        traceback.print_exc()
        return None

# ================================
# MAIN
# ================================
def main():
    print("🚀 Iniciando coleta de vídeos com #tylty...")

    posts = get_all_posts()
    if not posts:
        print("⚠️ Nenhum post retornado da API.")
        return

    filtered_posts = filter_posts(posts)
    if not filtered_posts:
        print("⚠️ Nenhum post com #tylty no período atual.")
        return

    ranking_df = generate_ranking(filtered_posts)
    if ranking_df.empty:
        print("⚠️ Ranking vazio, nada para salvar.")
        return

    excel_file = save_to_excel(ranking_df)
    if excel_file:
        print(f"✅ Ranking com gráfico salvo em:\n{excel_file}")

    print("🎯 Script finalizado!")

# ================================
# EXECUTAR SCRIPT
# ================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Erro inesperado no script: {e}")
        traceback.print_exc()

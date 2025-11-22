import os
import subprocess
import time
import psycopg2
import random
import tkinter as tk
from tkinter import filedialog, messagebox

# -------------------------------
# CONFIGURAÇÕES DO BANCO
# -------------------------------
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "n8n",
    "user": "n8n",
    "password": "n8npass"
}

# -------------------------------
# ESPERAR BANCO
# -------------------------------
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
    exit(1)

# -------------------------------
# CRIAR TABELA
# -------------------------------
def criar_tabela(conn, tabela):
    with conn.cursor() as cur:
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS "{tabela}" (
                id SERIAL PRIMARY KEY,
                nome_arquivo TEXT NOT NULL,
                legenda TEXT,
                titulo TEXT,
                status TEXT DEFAULT 'pendente',
                status_youtobe TEXT DEFAULT 'pendente',
                data_criacao TIMESTAMP DEFAULT NOW(),
                data_postagem TIMESTAMP
            )
        ''')
        conn.commit()
    print(f"✅ Tabela '{tabela}' verificada com sucesso.")

    # Adicionar coluna status_youtobe caso não exista
    with conn.cursor() as cur:
        cur.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = '{tabela}' AND column_name = 'status_youtobe'
                ) THEN
                    ALTER TABLE "{tabela}" ADD COLUMN status_youtobe TEXT DEFAULT 'pendente';
                END IF;
            END$$;
        """)
        conn.commit()

# -------------------------------
# INSERIR ARQUIVOS
# -------------------------------
def inserir_arquivos(conn, pasta, tabela, legendas):
    arquivos = [f for f in os.listdir(pasta) if os.path.isfile(os.path.join(pasta, f))]
    total_inseridos = 0

    with conn.cursor() as cur:
        for arquivo in arquivos:
            caminho_db = f"/caue/{tabela}/{arquivo}"  # <- Prefixo atualizado
            legenda = random.choice(legendas)

            cur.execute(f'''
                INSERT INTO "{tabela}" (nome_arquivo, legenda, titulo, status, status_youtobe, data_criacao)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            ''', (caminho_db, legenda, legenda, 'pendente', 'pendente'))

            total_inseridos += 1

        conn.commit()
    print(f"🎯 {total_inseridos} arquivos inseridos na tabela '{tabela}'.")

# -------------------------------
# TKINTER - SELEÇÃO DE PASTA E ARQUIVO
# -------------------------------
def selecionar_pasta():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.title("=== SELECIONE A PASTA DE VÍDEOS ===")
    pasta = filedialog.askdirectory(
        title="=== SELECIONE A PASTA DE VÍDEOS ==="
    )
    root.destroy()
    return pasta

def selecionar_legendas():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.title("=== SELECIONE O ARQUIVO DE LEGENDAS ===")
    arquivo = filedialog.askopenfilename(
        title="=== SELECIONE O ARQUIVO DE LEGENDAS ===",
        filetypes=[("Arquivos de Texto", "*.txt")]
    )
    root.destroy()
    return arquivo

# -------------------------------
# FUNÇÃO PRINCIPAL
# -------------------------------
def main():
    try:
        # Selecionar pasta de vídeos
        pasta = selecionar_pasta()
        if not pasta:
            messagebox.showerror("Erro", "Nenhuma pasta selecionada!")
            return

        tabela = os.path.basename(pasta.rstrip("/\\"))

        # Selecionar arquivo de legendas
        legendas_file = selecionar_legendas()
        if not legendas_file:
            messagebox.showerror("Erro", "Nenhum arquivo de legendas selecionado!")
            return

        with open(legendas_file, "r", encoding="utf-8-sig") as f:
            legendas = [x.strip() for x in f.read().split(",") if x.strip()]

        if not legendas:
            messagebox.showerror("Erro", "Nenhuma legenda encontrada no arquivo!")
            return

        # Conectar ao banco e inserir arquivos
        esperar_banco()
        conn = psycopg2.connect(**DB_CONFIG)
        criar_tabela(conn, tabela)
        inserir_arquivos(conn, pasta, tabela, legendas)
        conn.close()

        messagebox.showinfo("Sucesso", "🚀 Finalizado com sucesso!")

    except Exception as e:
        messagebox.showerror("Erro", str(e))

if __name__ == "__main__":
    main()

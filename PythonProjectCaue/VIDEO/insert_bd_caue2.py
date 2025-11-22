import os
import random
import psycopg2
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

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
# FUNÇÕES DO BANCO
# -------------------------------
def esperar_banco():
    print("⏳ Aguardando banco de dados...")
    import time
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
                data_postagem TIMESTAMP,
                data_post_youtube TIMESTAMP
            )
        ''')
        conn.commit()
    print(f"✅ Tabela '{tabela}' verificada com sucesso.")

def inserir_arquivos(conn, pasta, tabela, legendas, progress_bar, log_text, cancelar_event):
    arquivos = [f for f in os.listdir(pasta) if os.path.isfile(os.path.join(pasta, f))]
    total = len(arquivos)
    if total == 0:
        messagebox.showinfo("Aviso", "Nenhum arquivo encontrado na pasta.")
        return

    with conn.cursor() as cur:
        for i, arquivo in enumerate(arquivos, start=1):
            if cancelar_event.is_set():
                log_text.insert(tk.END, "\n🚫 Inserção cancelada pelo usuário.\n")
                break

            caminho_db = f"/caue/lucastylty_pr/{tabela}/{arquivo}"
            legenda = random.choice(legendas)
            cur.execute(f'''
                INSERT INTO "{tabela}" (nome_arquivo, legenda, titulo, status, status_youtobe, data_criacao)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            ''', (caminho_db, legenda, legenda, 'pendente', 'pendente'))

            log_text.insert(tk.END, f"✅ {arquivo} → inserido com legenda '{legenda}'\n")
            log_text.see(tk.END)

            progress_bar["value"] = (i / total) * 100
            progress_bar.update()

        conn.commit()
    messagebox.showinfo("Finalizado", f"🎯 Inserção concluída: {i}/{total} arquivos.")

# -------------------------------
# Seleção de pasta e arquivo
# -------------------------------
def selecionar_pasta(entry):
    pasta = filedialog.askdirectory()
    if pasta:
        entry.set(pasta)

def selecionar_legendas(entry):
    arquivo = filedialog.askopenfilename(
        title="=== SELECIONE O ARQUIVO DE LEGENDAS ===",
        filetypes=[("Arquivos de Texto", "*.txt")]
    )
    if arquivo:
        entry.set(arquivo)

# -------------------------------
# Iniciar processo em thread
# -------------------------------
def iniciar_processo(pasta_var, legendas_var, progress_bar, log_text, cancelar_event):
    pasta = pasta_var.get()
    legendas_file = legendas_var.get()

    if not pasta or not legendas_file:
        messagebox.showwarning("Aviso", "Selecione a pasta de vídeos e o arquivo de legendas!")
        return

    cancelar_event.clear()
    progress_bar["value"] = 0
    log_text.delete(1.0, tk.END)

    with open(legendas_file, "r", encoding="utf-8-sig") as f:
        legendas = [x.strip() for x in f.read().split(";") if x.strip()]

    if not legendas:
        messagebox.showerror("Erro", "Nenhuma legenda encontrada no arquivo!")
        return

    tabela = os.path.basename(pasta.rstrip("/\\"))
    esperar_banco()
    conn = psycopg2.connect(**DB_CONFIG)
    criar_tabela(conn, tabela)

    threading.Thread(
        target=inserir_arquivos,
        args=(conn, pasta, tabela, legendas, progress_bar, log_text, cancelar_event),
        daemon=True
    ).start()

# -------------------------------
# Interface gráfica principal
# -------------------------------
def main():
    root = tk.Tk()
    root.title("📝 Inserção de Arquivos no Banco")
    root.geometry("700x500")
    root.resizable(False, False)

    pasta_var = tk.StringVar()
    legendas_var = tk.StringVar()
    cancelar_event = threading.Event()

    frame = tk.Frame(root)
    frame.pack(pady=10)

    tk.Button(frame, text="📂 Selecionar Pasta de Vídeos",
              command=lambda: selecionar_pasta(pasta_var),
              width=25, bg="#2196F3", fg="white").grid(row=0, column=0, padx=5)
    tk.Label(frame, textvariable=pasta_var, width=55, anchor="w").grid(row=0, column=1)

    tk.Button(frame, text="📂 Selecionar Arquivo de Legendas",
              command=lambda: selecionar_legendas(legendas_var),
              width=25, bg="#4CAF50", fg="white").grid(row=1, column=0, padx=5, pady=5)
    tk.Label(frame, textvariable=legendas_var, width=55, anchor="w").grid(row=1, column=1)

    buttons_frame = tk.Frame(root)
    buttons_frame.pack(pady=10)

    progress_bar = ttk.Progressbar(root, length=650, mode="determinate")
    progress_bar.pack(pady=10)

    tk.Label(root, text="Log de Processamento:").pack(anchor="w", padx=10)
    log_text = tk.Text(root, width=85, height=12)
    log_text.pack(padx=10, pady=5)

    tk.Button(buttons_frame, text="🚀 Iniciar Inserção", width=25, height=2,
              bg="#FF5722", fg="white", font=("Arial", 11, "bold"),
              command=lambda: iniciar_processo(pasta_var, legendas_var, progress_bar, log_text, cancelar_event)).grid(row=0, column=0, padx=10)

    tk.Button(buttons_frame, text="🛑 Cancelar", width=25, height=2,
              bg="#F44336", fg="white", font=("Arial", 11, "bold"),
              command=cancelar_event.set).grid(row=0, column=1, padx=10)

    tk.Checkbutton(root, text="Ativar logs detalhados", variable=cancelar_event).pack(anchor="w", padx=15, pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()

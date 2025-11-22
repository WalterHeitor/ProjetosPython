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
# Funções Banco
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
    print("❌ Banco não respondeu!")
    exit(1)

def atualizar_tabela(conn, tabela, legendas, progress_bar, log_text, cancelar_event):
    with conn.cursor() as cur:
        # Conta total
        cur.execute(f'SELECT COUNT(*) FROM "{tabela}" WHERE status = %s', ('pendente',))
        total = cur.fetchone()[0]

        if total == 0:
            messagebox.showinfo("Aviso", f"Nenhum registro pendente em '{tabela}'.")
            return

        # Busca pendentes
        # cur.execute(f'''
        #     SELECT id, nome_arquivo
        #     FROM "{tabela}"
        #     WHERE status = 'pendente'
        #     ORDER BY id ASC
        # ''')
        cur.execute(f'''
            SELECT id, nome_arquivo 
            FROM "{tabela}"
            ORDER BY id ASC
        ''')

        registros = cur.fetchall()

        for i, (id_reg, arquivo) in enumerate(registros, start=1):
            if cancelar_event.is_set():
                log_text.insert(tk.END, "\n🚫 Atualização cancelada pelo usuário.\n")
                break

            legenda = random.choice(legendas)

            cur.execute(f'''
                UPDATE "{tabela}"
                SET legenda = %s,
                    titulo = %s
                WHERE id = %s
            ''', (legenda, legenda, id_reg))

            log_text.insert(tk.END, f"🔄 ID {id_reg} atualizado → '{legenda}'\n")
            log_text.see(tk.END)

            progress_bar["value"] = (i / total) * 100
            progress_bar.update()

        conn.commit()

    messagebox.showinfo("Finalizado", f"🎯 Atualização concluída: {i}/{total} registros.")

# -------------------------------
# Selecionar arquivo TXT
# -------------------------------
def selecionar_legendas(entry):
    arquivo = filedialog.askopenfilename(
        title="=== SELECIONE O ARQUIVO DE LEGENDAS ===",
        filetypes=[("Arquivos de Texto", "*.txt")]
    )
    if arquivo:
        entry.set(arquivo)

# -------------------------------
# Iniciar processo
# -------------------------------
def iniciar_processo(tabela_var, legendas_var, progress_bar, log_text, cancelar_event):
    tabela = tabela_var.get().strip()
    legendas_file = legendas_var.get()

    if not tabela:
        messagebox.showwarning("Aviso", "Digite o nome da tabela!")
        return

    if not legendas_file:
        messagebox.showwarning("Aviso", "Selecione o arquivo de legendas!")
        return

    cancelar_event.clear()
    progress_bar["value"] = 0
    log_text.delete(1.0, tk.END)

    with open(legendas_file, "r", encoding="utf-8-sig") as f:
        legendas = [x.strip() for x in f.read().split(";") if x.strip()]

    if not legendas:
        messagebox.showerror("Erro", "Nenhuma legenda encontrada no arquivo!")
        return

    esperar_banco()
    conn = psycopg2.connect(**DB_CONFIG)

    threading.Thread(
        target=atualizar_tabela,
        args=(conn, tabela, legendas, progress_bar, log_text, cancelar_event),
        daemon=True
    ).start()

# -------------------------------
# Interface gráfica
# -------------------------------
def main():
    root = tk.Tk()
    root.title("🔄 Atualização de Tabela Existente")
    root.geometry("700x470")
    root.resizable(False, False)

    tabela_var = tk.StringVar()
    legendas_var = tk.StringVar()
    cancelar_event = threading.Event()

    frame = tk.Frame(root)
    frame.pack(pady=10)

    # Campo para digitar a tabela
    tk.Label(frame, text="Nome da Tabela:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
    tk.Entry(frame, textvariable=tabela_var, width=35).grid(row=0, column=1, padx=10)

    # Selecionar arquivo de legendas
    tk.Button(frame, text="📂 Selecionar Arquivo de Legendas",
              command=lambda: selecionar_legendas(legendas_var),
              width=30, bg="#4CAF50", fg="white").grid(row=1, column=0, padx=5, pady=5)

    tk.Label(frame, textvariable=legendas_var, width=45, anchor="w").grid(row=1, column=1)

    buttons_frame = tk.Frame(root)
    buttons_frame.pack(pady=10)

    progress_bar = ttk.Progressbar(root, length=650, mode="determinate")
    progress_bar.pack(pady=10)

    tk.Label(root, text="Log de Atualização:").pack(anchor="w", padx=10)
    log_text = tk.Text(root, width=85, height=12)
    log_text.pack(padx=10, pady=5)

    tk.Button(buttons_frame, text="🚀 Iniciar Atualização", width=25, height=2,
              bg="#FF9800", fg="white", font=("Arial", 11, "bold"),
              command=lambda: iniciar_processo(tabela_var, legendas_var, progress_bar, log_text, cancelar_event)).grid(row=0, column=0, padx=10)

    tk.Button(buttons_frame, text="🛑 Cancelar", width=25, height=2,
              bg="#F44336", fg="white", font=("Arial", 11, "bold"),
              command=cancelar_event.set).grid(row=0, column=1, padx=10)

    root.mainloop()

if __name__ == "__main__":
    main()

import os
import shutil
import re
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import unicodedata

# -------------------------------
# Configuração inicial
# -------------------------------
FORMATOS_SUPORTADOS = (".mp4", ".mkv", ".mov", ".avi", ".webm")
LOG_ERROS = "log_erros.txt"

# -------------------------------
# Função para limpar nomes de arquivos
# -------------------------------
def limpar_nome_arquivo(nome):
    nome = unicodedata.normalize('NFD', nome).encode('ascii', 'ignore').decode('utf-8')
    nome = nome.replace(" ", "_")
    nome = re.sub(r'[^a-zA-Z0-9._-]', '', nome)
    nome = re.sub(r'_+', '_', nome)
    return nome.lower()

# -------------------------------
# Função principal de cópia e renomeação
# -------------------------------
def copiar_e_renomear(pasta_origem, pasta_destino, progress_bar, log_text, cancelar_event):
    os.makedirs(pasta_destino, exist_ok=True)
    arquivos = [f for f in os.listdir(pasta_origem) if f.lower().endswith(FORMATOS_SUPORTADOS)]
    total = len(arquivos)

    if total == 0:
        messagebox.showinfo("Aviso", "Nenhum arquivo de vídeo encontrado na pasta de origem.")
        return

    erros = []

    for i, arquivo in enumerate(arquivos, start=1):
        if cancelar_event.is_set():
            log_text.insert(tk.END, "\n🚫 Processamento cancelado pelo usuário.\n")
            break

        try:
            caminho_origem = os.path.join(pasta_origem, arquivo)
            nome_limpo = limpar_nome_arquivo(arquivo)
            caminho_destino = os.path.join(pasta_destino, nome_limpo)

            # Evita sobrescrever arquivos existentes
            base, ext = os.path.splitext(caminho_destino)
            contador = 1
            while os.path.exists(caminho_destino):
                caminho_destino = f"{base}_{contador}{ext}"
                contador += 1

            shutil.copy(caminho_origem, caminho_destino)

            log_text.insert(tk.END, f"✅ {arquivo} → {os.path.basename(caminho_destino)}\n")
            log_text.see(tk.END)

            progress_bar["value"] = (i / total) * 100
            progress_bar.update()
        except Exception as e:
            erros.append(f"{arquivo} → {e}")

    if erros:
        with open(LOG_ERROS, "w", encoding="utf-8") as f:
            f.write("\n".join(erros))
        messagebox.showwarning("Aviso", f"Alguns arquivos falharam. Veja {LOG_ERROS} para detalhes.")

    messagebox.showinfo("Finalizado", f"🎯 Renomeação concluída: {i}/{total} vídeos.")

# -------------------------------
# Selecionar pasta
# -------------------------------
def selecionar_pasta(entry):
    pasta = filedialog.askdirectory()
    if pasta:
        entry.set(pasta)

# -------------------------------
# Iniciar processamento
# -------------------------------
def iniciar_processo(origem, destino, progress_bar, log_text, cancelar_event):
    pasta_origem = origem.get()
    pasta_destino = destino.get()

    if not pasta_origem or not pasta_destino:
        messagebox.showwarning("Aviso", "Selecione as pastas de origem e destino!")
        return

    cancelar_event.clear()

    threading.Thread(
        target=copiar_e_renomear,
        args=(pasta_origem, pasta_destino, progress_bar, log_text, cancelar_event),
        daemon=True
    ).start()

# -------------------------------
# Interface gráfica principal
# -------------------------------
def main():
    root = tk.Tk()
    root.title("📁 Renomeador de Vídeos")
    root.geometry("700x500")
    root.resizable(False, False)

    pasta_origem = tk.StringVar()
    pasta_destino = tk.StringVar()
    cancelar_event = threading.Event()

    frame = tk.Frame(root)
    frame.pack(pady=10)

    tk.Button(frame, text="📂 Pasta de Origem",
              command=lambda: selecionar_pasta(pasta_origem),
              width=25, bg="#2196F3", fg="white").grid(row=0, column=0, padx=5)
    tk.Label(frame, textvariable=pasta_origem, width=55, anchor="w").grid(row=0, column=1)

    tk.Button(frame, text="📂 Pasta de Destino",
              command=lambda: selecionar_pasta(pasta_destino),
              width=25, bg="#4CAF50", fg="white").grid(row=1, column=0, padx=5, pady=5)
    tk.Label(frame, textvariable=pasta_destino, width=55, anchor="w").grid(row=1, column=1)

    buttons_frame = tk.Frame(root)
    buttons_frame.pack(pady=5)

    tk.Button(buttons_frame, text="🚀 Iniciar", width=25, height=2,
              bg="#FF9800", fg="white", font=("Arial", 11, "bold"),
              command=lambda: iniciar_processo(pasta_origem, pasta_destino, progress_bar, log_text, cancelar_event)).grid(row=0, column=0, padx=10)

    tk.Button(buttons_frame, text="🛑 Cancelar", width=25, height=2,
              bg="#F44336", fg="white", font=("Arial", 11, "bold"),
              command=cancelar_event.set).grid(row=0, column=1, padx=10)

    progress_bar = ttk.Progressbar(root, length=650, mode="determinate")
    progress_bar.pack(pady=10)

    tk.Label(root, text="Log de Renomeação:").pack(anchor="w", padx=10)
    log_text = tk.Text(root, width=85, height=12)
    log_text.pack(padx=10, pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()

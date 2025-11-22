import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import unicodedata
import re
import threading
import subprocess


# Função para limpar nome dos arquivos
def limpar_nome_arquivo(nome):
    nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    nome = re.sub(r'[^a-zA-Z0-9._-]', '_', nome)
    return nome.lower()


# Função para garantir compatibilidade dos vídeos
def converter_video(input_path, output_path):
    """
    Converte o vídeo para MP4 (H.264 + AAC), máximo 1080p, 30 fps
    """
    comando = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", "scale='min(1080,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "fast",
        "-b:v", "5000k",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ac", "2",
        output_path
    ]
    try:
        subprocess.run(comando, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


# Função para processar vídeos
def processar_videos(pasta_entrada, pasta_saida, progresso, log_text, btn_cancelar):
    erros = []
    arquivos = [f for f in os.listdir(pasta_entrada) if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))]

    total = len(arquivos)
    for i, arquivo in enumerate(arquivos, start=1):
        if cancelado[0]:
            log_text.insert(tk.END, "\n🚫 Operação cancelada pelo usuário!\n")
            break

        caminho_entrada = os.path.join(pasta_entrada, arquivo)
        nome_limpo = limpar_nome_arquivo(os.path.splitext(arquivo)[0]) + ".mp4"
        caminho_saida = os.path.join(pasta_saida, nome_limpo)

        log_text.insert(tk.END, f"\n📂 Processando: {arquivo} → {nome_limpo}\n")
        log_text.see(tk.END)

        sucesso = converter_video(caminho_entrada, caminho_saida)

        if sucesso:
            log_text.insert(tk.END, f"✅ Convertido com sucesso para {caminho_saida}\n")
        else:
            log_text.insert(tk.END, f"❌ Erro ao converter {arquivo}\n")
            erros.append(arquivo)

        progresso['value'] = (i / total) * 100
        root.update_idletasks()

    if erros:
        with open("log_erros.txt", "w") as f:
            f.write("\n".join(erros))
        messagebox.showerror("Erros", f"Alguns vídeos falharam. Verifique 'log_erros.txt'.")
    else:
        messagebox.showinfo("Concluído", "Todos os vídeos foram convertidos com sucesso!")


# Funções da interface
def selecionar_pasta_entrada():
    pasta = filedialog.askdirectory()
    if pasta:
        entry_entrada.delete(0, tk.END)
        entry_entrada.insert(0, pasta)


def selecionar_pasta_saida():
    pasta = filedialog.askdirectory()
    if pasta:
        entry_saida.delete(0, tk.END)
        entry_saida.insert(0, pasta)


def iniciar_processamento():
    pasta_entrada = entry_entrada.get()
    pasta_saida = entry_saida.get()

    if not pasta_entrada or not pasta_saida:
        messagebox.showwarning("Aviso", "Selecione as pastas de entrada e saída.")
        return

    cancelado[0] = False
    btn_cancelar.config(state="normal")

    thread = threading.Thread(target=processar_videos, args=(pasta_entrada, pasta_saida, progresso, log_text, btn_cancelar))
    thread.start()


def cancelar():
    cancelado[0] = True
    btn_cancelar.config(state="disabled")


# ======================
# MAIN
# ======================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Organizador e Conversor de Vídeos")
    root.geometry("600x500")

    cancelado = [False]

    frame = tk.Frame(root)
    frame.pack(pady=10)

    tk.Label(frame, text="Pasta de Entrada:").grid(row=0, column=0, sticky="w")
    entry_entrada = tk.Entry(frame, width=50)
    entry_entrada.grid(row=0, column=1)
    btn_entrada = tk.Button(frame, text="Selecionar", command=selecionar_pasta_entrada)
    btn_entrada.grid(row=0, column=2)

    tk.Label(frame, text="Pasta de Saída:").grid(row=1, column=0, sticky="w")
    entry_saida = tk.Entry(frame, width=50)
    entry_saida.grid(row=1, column=1)
    btn_saida = tk.Button(frame, text="Selecionar", command=selecionar_pasta_saida)
    btn_saida.grid(row=1, column=2)

    btn_iniciar = tk.Button(root, text="Iniciar", command=iniciar_processamento, bg="green", fg="white")
    btn_iniciar.pack(pady=5)

    btn_cancelar = tk.Button(root, text="Cancelar", command=cancelar, bg="red", fg="white", state="disabled")
    btn_cancelar.pack(pady=5)

    progresso = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
    progresso.pack(pady=10)

    log_text = tk.Text(root, height=15, width=70)
    log_text.pack(pady=10)

    root.mainloop()

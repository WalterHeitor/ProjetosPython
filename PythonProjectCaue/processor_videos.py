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


# Função para garantir compatibilidade dos vídeos (usando GPU para vídeo e CPU para áudio)
def converter_video(input_path, output_path):
    """
    Converte o vídeo para MP4 (H.264 + AAC), usando NVENC para acelerar a codificação de vídeo,
    e CPU para a codificação de áudio (máximo 1080p, 30 fps)
    """
    comando = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", "scale='min(1080,iw)':'min(1920,ih)':force_original_aspect_ratio=decrease",
        "-r", "30",
        "-c:v", "h264_nvenc",  # Usando a GPU para codificação de vídeo
        "-preset", "fast",  # Acelera a codificação do vídeo
        "-b:v", "5000k",
        "-c:a", "aac",  # Usando CPU para codificação de áudio
        "-b:a", "192k",
        "-ac", "2",  # Configuração de áudio em estéreo
        output_path
    ]
    try:
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
    root.title("🎬 Organizador e Conversor de Vídeos")
    root.geometry("680x560")
    root.configure(bg="#1e1e1e")

    cancelado = [False]

    # 🎨 Estilo moderno com botões arredondados e sombra
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "TButton",
        font=("Segoe UI", 10, "bold"),
        padding=8,
        relief="flat",
        background="#4CAF50",
        foreground="white",
        borderwidth=0
    )
    style.map(
        "TButton",
        background=[("active", "#45a049")]
    )

    # Barra de progresso personalizada
    style.configure(
        "TProgressbar",
        thickness=20,
        troughcolor="#333333",
        background="#4CAF50",
        bordercolor="#1e1e1e"
    )

    # Função para criar botões arredondados com sombra
    def criar_botao(texto, comando, cor="#4CAF50"):
        frame_btn = tk.Frame(root, bg="#1e1e1e")
        frame_btn.pack(pady=5)
        sombra = tk.Label(frame_btn, text=texto, bg="#000000", fg="white",
                          font=("Segoe UI", 10, "bold"), width=20)
        sombra.place(x=2, y=2)
        botao = tk.Button(
            frame_btn,
            text=texto,
            command=comando,
            font=("Segoe UI", 10, "bold"),
            bg=cor,
            fg="white",
            activebackground="#45a049",
            activeforeground="white",
            bd=0,
            relief="flat",
            width=20,
            height=1,
            highlightthickness=0
        )
        botao.pack()
        return botao

    frame = tk.Frame(root, bg="#1e1e1e")
    frame.pack(pady=15)

    tk.Label(frame, text="📂 Pasta de Entrada:", font=("Segoe UI", 10, "bold"), bg="#1e1e1e", fg="white").grid(row=0, column=0, sticky="w", pady=5)
    entry_entrada = tk.Entry(frame, width=50, font=("Segoe UI", 9))
    entry_entrada.grid(row=0, column=1, padx=5)
    btn_entrada = ttk.Button(frame, text="Selecionar", command=selecionar_pasta_entrada)
    btn_entrada.grid(row=0, column=2, padx=5)

    tk.Label(frame, text="💾 Pasta de Saída:", font=("Segoe UI", 10, "bold"), bg="#1e1e1e", fg="white").grid(row=1, column=0, sticky="w", pady=5)
    entry_saida = tk.Entry(frame, width=50, font=("Segoe UI", 9))
    entry_saida.grid(row=1, column=1, padx=5)
    btn_saida = ttk.Button(frame, text="Selecionar", command=selecionar_pasta_saida)
    btn_saida.grid(row=1, column=2, padx=5)

    # Botões com sombra e cantos arredondados
    btn_iniciar = criar_botao("🚀 Iniciar Conversão", iniciar_processamento, cor="#4CAF50")
    btn_cancelar = criar_botao("❌ Cancelar", cancelar, cor="#E74C3C")
    btn_cancelar.config(state="disabled")

    progresso = ttk.Progressbar(root, orient="horizontal", length=480, mode="determinate")
    progresso.pack(pady=15)

    log_frame = tk.Frame(root, bg="#1e1e1e")
    log_frame.pack(pady=10)
    tk.Label(log_frame, text="📜 Log de Processamento:", font=("Segoe UI", 10, "bold"), bg="#1e1e1e", fg="white").pack(anchor="w")
    log_text = tk.Text(log_frame, height=15, width=80, bg="#2d2d2d", fg="#00ff88", insertbackground="white", font=("Consolas", 9))
    log_text.pack()

    root.mainloop()

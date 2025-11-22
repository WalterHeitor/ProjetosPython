import os
import subprocess
import time
import psycopg2
import random
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "n8n",
    "user": "n8n",
    "password": "n8npass"
}

class App:
    def __init__(self, root):
        self.root = root
        root.title("📂 Processamento de Vídeos")
        root.geometry("600x300")
        root.configure(bg="#4B5320")  # verde exército

        # Título da etapa
        self.label_title = tk.Label(root, text="", font=("Arial", 22, "bold"),
                                    fg="#FFFFE0", bg="#4B5320")
        self.label_title.pack(pady=20)

        # Mensagem da etapa
        self.label_message = tk.Label(root, text="", font=("Arial", 14),
                                      fg="white", bg="#4B5320", wraplength=550, justify="center")
        self.label_message.pack(pady=10)

        # Barra de progresso
        self.progress = ttk.Progressbar(root, length=400, mode="determinate", maximum=5, value=0)
        self.progress.pack(pady=15)

        # Botão próximo (opcional)
        self.button_next = tk.Button(root, text="Iniciar Processo", font=("Arial", 14, "bold"),
                                     bg="#A9BA9D", fg="#1B1B1B", width=15, height=2,
                                     command=self.run_process)
        self.button_next.pack(pady=20)

    def update_stage(self, stage, message, value):
        self.label_title.config(text=stage)
        self.label_message.config(text=message)
        self.progress['value'] = value
        self.root.update()

    def run_process(self):
        # Apaga o botão assim que clicar
        self.button_next.destroy()
        try:
            # Etapa 1 - Seleção da pasta de vídeos
            self.update_stage("Etapa 1 - Seleção de Vídeos",
                              "Escolha a pasta que contém os vídeos para processamento.", 1)
            pasta = filedialog.askdirectory(title="Selecione a pasta de vídeos")
            if not pasta:
                messagebox.showerror("Erro", "Nenhuma pasta selecionada!")
                return
            tabela = os.path.basename(pasta.rstrip("/\\"))
            prefix = tabela

            # Etapa 2 - Seleção do arquivo de legendas
            self.update_stage("Etapa 2 - Seleção das Legendas",
                              "Selecione o arquivo de legendas (.txt) com frases separadas por vírgula.", 2)
            legendas_file = filedialog.askopenfilename(
                title="Selecione o arquivo de legendas",
                filetypes=[("Arquivos de Texto", "*.txt")]
            )
            if not legendas_file:
                messagebox.showerror("Erro", "Nenhum arquivo de legendas selecionado!")
                return
            with open(legendas_file, "r", encoding="utf-8-sig") as f:
                legendas = [x.strip() for x in f.read().split(",") if x.strip()]
            if not legendas:
                messagebox.showerror("Erro", "Nenhuma legenda encontrada no arquivo!")
                return

            # Etapa 3 - Copiando vídeos
            self.update_stage("Etapa 3 - Preparando Vídeos",
                              "Os vídeos serão copiados para a pasta do Docker.", 3)
            pasta_docker = self.copiar_videos(pasta, tabela)

            # Etapa 4 - Subindo containers
            self.update_stage("Etapa 4 - Subindo Containers",
                              "Inicializando containers Docker...", 4)
            self.start_docker()
            self.esperar_banco()

            # Etapa 5 - Criando tabela e inserindo dados
            self.update_stage("Etapa 5 - Inserindo no Banco",
                              "Criando tabela e inserindo arquivos no banco de dados...", 5)
            conn = psycopg2.connect(**DB_CONFIG)
            self.criar_tabela(conn, tabela)
            self.inserir_arquivos(conn, pasta, prefix, legendas, tabela)
            conn.close()

            self.update_stage("✅ Processo Finalizado",
                              "Todos os vídeos foram copiados, o banco atualizado e os containers configurados com sucesso!", 5)
            # Mensagem final SoftNequeSi
            self.update_stage("🎉 SoftNequeSi", "Processo concluído com sucesso!", 100)

            # Atualiza a tela
            self.root.update()

            # Pausa para o usuário enxergar a mensagem final
            time.sleep(2)

            # Fecha a janela
            self.root.destroy()

        except Exception as e:
            messagebox.showerror("Erro", str(e))
        finally:
            self.stop_docker()

    # ---------------- Docker e banco ----------------
    def start_docker(self):
        subprocess.run(["docker-compose", "up", "-d"], check=True)

    def stop_docker(self):
        subprocess.run(["docker-compose", "down"], check=True)

    def esperar_banco(self):
        for _ in range(30):
            try:
                conn = psycopg2.connect(**DB_CONFIG)
                conn.close()
                return
            except psycopg2.OperationalError:
                time.sleep(2)
        raise Exception("Banco de dados não respondeu a tempo!")

    def criar_tabela(self, conn, tabela):
        with conn.cursor() as cur:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS "{tabela}" (
                    id SERIAL PRIMARY KEY,
                    nome_arquivo TEXT NOT NULL,
                    legenda TEXT,
                    status TEXT DEFAULT 'pendente',
                    data_criacao TIMESTAMP DEFAULT NOW(),
                    data_postagem TIMESTAMP
                )
            ''')
            conn.commit()

    def inserir_arquivos(self, conn, pasta, prefix, legendas, tabela):
        arquivos = [f for f in os.listdir(pasta) if os.path.isfile(os.path.join(pasta, f))]
        with conn.cursor() as cur:
            for arquivo in arquivos:
                caminho_db = f"/{prefix}/{arquivo}"
                legenda = random.choice(legendas)
                cur.execute(f'''
                    INSERT INTO "{tabela}" (nome_arquivo, legenda, status, data_criacao)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT DO NOTHING
                ''', (caminho_db, legenda, 'pendente'))
            conn.commit()

    def copiar_videos(self, origem, pasta_nome):
        destino = os.path.join(os.getcwd(), "videos", pasta_nome)
        os.makedirs(destino, exist_ok=True)
        arquivos = [f for f in os.listdir(origem) if os.path.isfile(os.path.join(origem, f))]
        for arquivo in arquivos:
            shutil.copy2(os.path.join(origem, arquivo), os.path.join(destino, arquivo))
        return destino

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()

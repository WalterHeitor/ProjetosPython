"""
GERADOR LOTOFÁCIL — focado só no que a matemática comprova

O backtest (lotofacil_laboratorio.py) mostrou que frequência, atraso e IA
NÃO aumentam a chance de acerto. Então este gerador faz só o que tem efeito real:

 1. Dezenas 100% aleatórias (gerador criptográfico): todas as combinações
    têm a mesma chance, e nenhum viés pessoal entra no jogo.
 2. Evita jogos POPULARES (sequências, linhas/colunas inteiras da cartela,
    só ímpares/pares, moldura, resultados passados). A chance é a mesma, mas
    se ganhar você divide o prêmio com menos gente.
 3. Diversifica os jogos entre si (menor sobreposição possível): suas apostas
    cobrem mais dezenas diferentes em vez de repetir as mesmas.
"""
import datetime
import os
import secrets
from collections import Counter
from tkinter import Tk, filedialog, messagebox, simpledialog

import pandas as pd

try:
    from lotofacil_laboratorio import carregar_historico
except ImportError:
    carregar_historico = None

# -----------------------------
# CONFIG
# -----------------------------
NUM_JOGOS_PADRAO = 8
DEZENAS_JOGO = 15
CANDIDATOS_POR_JOGO = 3000      # quanto maior, mais diversificados os jogos
MAX_SEQUENCIA = 6               # maior sequência de consecutivas permitida (ex: 7-8-9-10-11-12)
MAX_IGUAIS_HISTORICO = 13       # rejeita jogo com 14/15 dezenas iguais a um resultado passado
MIN_PARES, MAX_PARES = 4, 11    # fora disso é padrão "só ímpares / só pares"

LINHAS = [set(range(r * 5 + 1, r * 5 + 6)) for r in range(5)]
COLUNAS = [set(range(c + 1, 26, 5)) for c in range(5)]
DIAGONAIS = [{1, 7, 13, 19, 25}, {5, 9, 13, 17, 21}]
MOLDURA = set(range(1, 6)) | set(range(21, 26)) | {6, 11, 16, 10, 15, 20}

rng = secrets.SystemRandom()


# -----------------------------
# FILTRO ANTI-POPULAR
# -----------------------------
def maior_sequencia(jogo):
    maior = atual = 1
    for a, b in zip(jogo, jogo[1:]):
        atual = atual + 1 if b == a + 1 else 1
        maior = max(maior, atual)
    return maior


def eh_popular(jogo, historico):
    s = set(jogo)
    if maior_sequencia(jogo) > MAX_SEQUENCIA:
        return True                                   # 1-2-3-4-5-6-7...
    linhas_cheias = sum(l <= s for l in LINHAS)
    colunas_cheias = sum(c <= s for c in COLUNAS)
    if linhas_cheias + colunas_cheias >= 2:
        return True                                   # desenhos na cartela
    if all(d <= s for d in DIAGONAIS):
        return True                                   # "X" na cartela
    if len(s & MOLDURA) >= 15 or len(s - MOLDURA) == 9:
        return True                                   # moldura / miolo completo
    pares = sum(1 for d in jogo if d % 2 == 0)
    if not (MIN_PARES <= pares <= MAX_PARES):
        return True                                   # só ímpares / só pares
    if all(d % 5 == 0 or d % 3 == 0 for d in jogo):
        return True                                   # múltiplos
    for h in historico:
        if len(s & h) > MAX_IGUAIS_HISTORICO:
            return True                               # repetir resultado antigo
    return False


# -----------------------------
# GERAÇÃO COM DIVERSIFICAÇÃO
# -----------------------------
def jogo_aleatorio():
    return sorted(rng.sample(range(1, 26), DEZENAS_JOGO))


def custo(jogo, escolhidos, uso):
    """Menor é melhor: sobreposição máxima e total com os jogos já escolhidos,
    e preferência por dezenas menos usadas até agora (cobertura equilibrada)."""
    if not escolhidos:
        return (0, 0, 0)
    s = set(jogo)
    inter = [len(s & set(e)) for e in escolhidos]
    return (max(inter), sum(inter), sum(uso[d] for d in jogo))


def gerar(num_jogos, historico):
    escolhidos = []
    uso = Counter()
    for _ in range(num_jogos):
        melhor, melhor_custo = None, None
        for _ in range(CANDIDATOS_POR_JOGO):
            j = jogo_aleatorio()
            if j in escolhidos:
                continue
            c = custo(j, escolhidos, uso)
            # checagem cara (histórico) só para quem já é o melhor candidato
            if (melhor_custo is None or c < melhor_custo) and not eh_popular(j, historico):
                melhor, melhor_custo = j, c
        escolhidos.append(melhor)
        uso.update(melhor)
    return escolhidos


# -----------------------------
# SAÍDA
# -----------------------------
def salvar_excel(jogos, pasta):
    linhas = []
    for i, jogo in enumerate(jogos):
        outros = [set(o) for k, o in enumerate(jogos) if k != i]
        linha = {f"D{k + 1}": d for k, d in enumerate(jogo)}
        linha["Pares"] = sum(1 for d in jogo if d % 2 == 0)
        linha["Soma"] = sum(jogo)
        linha["Max_iguais_outro_jogo"] = max((len(set(jogo) & o) for o in outros), default=0)
        linhas.append(linha)
    df = pd.DataFrame(linhas)
    data = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    caminho = os.path.join(pasta, f"lotofacil_gerador_inteligente_{data}.xlsx")
    df.to_excel(caminho, index=False)
    return caminho


def carregar_historico_sets():
    if carregar_historico is None:
        return []
    try:
        dados = carregar_historico()
        return [{int(d) for d in c["dezenas"]} for c in dados]
    except Exception:
        return []        # sem internet e sem cache: segue sem esse filtro


def main():
    root = Tk()
    root.withdraw()

    num = simpledialog.askinteger("Lotofácil", "Quantos jogos gerar?",
                                  initialvalue=NUM_JOGOS_PADRAO, minvalue=1, maxvalue=200)
    if not num:
        return
    pasta = filedialog.askdirectory(title="Selecione a pasta de saída")
    if not pasta:
        return

    historico = carregar_historico_sets()
    jogos = gerar(num, historico)
    caminho = salvar_excel(jogos, pasta)

    cobertura = len(set().union(*map(set, jogos)))
    max_iguais = max((len(set(a) & set(b)) for i, a in enumerate(jogos)
                      for b in jogos[i + 1:]), default=0)
    aviso_hist = (f"{len(historico)} resultados passados evitados"
                  if historico else "histórico indisponível (filtro de resultados passados desligado)")

    messagebox.showinfo(
        "Sucesso",
        f"✅ {len(jogos)} jogos gerados\n\n"
        f"Dezenas cobertas: {cobertura}/25\n"
        f"Máx. dezenas iguais entre dois jogos: {max_iguais} "
        f"(jogos aleatórios comuns: ~9 em média)\n"
        f"Anti-popular: {aviso_hist}\n\n"
        f"📁 {caminho}\n\n"
        "⚠️ Cada jogo tem 1 chance em 3.268.760 de fazer 15 pontos, como qualquer outro. "
        "O gerador não aumenta essa chance: ele evita dividir o prêmio e evita "
        "apostas repetidas entre si."
    )


if __name__ == "__main__":
    main()

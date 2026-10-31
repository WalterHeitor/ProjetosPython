"""
LABORATÓRIO LOTOFÁCIL — teste científico de modelos de "previsão"

O que faz:
 1. Baixa (ou usa cache) o histórico oficial completo.
 2. Testes de aleatoriedade: o sorteio é uniforme? Há memória entre concursos?
 3. Backtest walk-forward: cada modelo só enxerga o passado de cada concurso
    e escolhe 15 dezenas. Compara com o acaso (média teórica = 9,0 acertos).
    Modelos: aleatório, quentes, frias(atraso), método composto (o seu),
    regressão logística e gradient boosting (IA) sobre várias features.
 4. Valor esperado da aposta com os prêmios reais pagos.

Uso:  python lotofacil_laboratorio.py
"""
import json
import math
import os
import random
import urllib.request
from collections import Counter

import numpy as np
from scipy import stats
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(AQUI, "dados", "lotofacil_historico.json")
URL = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
PRECO_APOSTA = 3.50          # aposta simples de 15 dezenas
INICIO_TESTE = 2800          # concursos usados só para treino antes do teste
RETREINO_A_CADA = 100        # modelos de IA são re-treinados a cada N concursos
SEMENTE = 42


# ---------------------------------------------------------------- dados
def carregar_historico(atualizar=False):
    if atualizar or not os.path.exists(CACHE):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            dados = json.loads(r.read().decode("utf-8"))
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False)
    with open(CACHE, encoding="utf-8") as f:
        dados = json.load(f)
    dados.sort(key=lambda c: c["concurso"])
    return dados


def matriz_sorteios(dados):
    """M[t, d-1] = 1 se a dezena d saiu no concurso t."""
    M = np.zeros((len(dados), 25), dtype=np.int8)
    for t, c in enumerate(dados):
        for d in c["dezenas"]:
            M[t, int(d) - 1] = 1
    return M


# ---------------------------------------------------------------- 1. aleatoriedade
def testes_aleatoriedade(M):
    T = len(M)
    print("\n=== 1. O SORTEIO É ALEATÓRIO? ===")
    freq = M.sum(axis=0)
    esperado = T * 15 / 25
    chi2, p = stats.chisquare(freq, [esperado] * 25)
    print(f"Concursos: {T}. Frequência esperada por dezena: {esperado:.0f}")
    print(f"Mais saiu: {freq.argmax()+1:02d} ({freq.max()}x)  |  Menos saiu: {freq.argmin()+1:02d} ({freq.min()}x)")
    print(f"Qui-quadrado uniformidade: p = {p:.3f}  "
          f"({'compatível com sorteio justo' if p > 0.05 else 'desvio significativo'})")

    # memória: a dezena que saiu ontem sai mais hoje?
    repete = (M[1:] & M[:-1]).sum() / M[:-1].sum()
    print(f"P(sair | saiu no concurso anterior) = {repete:.4f}   (acaso = 0.6000)")

    # atraso: dezena atrasada sai mais?
    print("\nP(sair) conforme o atraso (concursos sem sair):")
    atraso = np.zeros(25, dtype=int)
    cont = Counter()
    hits = Counter()
    for t in range(T):
        for d in range(25):
            b = min(atraso[d], 5)
            cont[b] += 1
            hits[b] += int(M[t, d])
        atraso = np.where(M[t] == 1, 0, atraso + 1)
    for b in range(6):
        rot = f"{b}+" if b == 5 else str(b)
        taxa = hits[b] / cont[b]
        ic = 1.96 * math.sqrt(0.6 * 0.4 / cont[b])
        print(f"  atraso {rot:>2}: {taxa:.4f}  (n={cont[b]:6d}, acaso 0.6000 ± {ic:.4f})")


# ---------------------------------------------------------------- features p/ IA
def construir_features(M):
    """Para cada concurso t e dezena d, features calculadas SÓ com t-1, t-2, ..."""
    T = len(M)
    X = np.zeros((T, 25, 9), dtype=np.float32)
    cum = np.vstack([np.zeros((1, 25)), np.cumsum(M, axis=0)])
    atraso = np.zeros(25)
    for t in range(T):
        for j, w in enumerate((5, 10, 25, 100)):
            a = max(0, t - w)
            X[t, :, j] = (cum[t] - cum[a]) / max(1, t - a)
        X[t, :, 4] = cum[t] / max(1, t)              # freq. histórica total
        X[t, :, 5] = atraso
        X[t, :, 6] = M[t - 1] if t >= 1 else 0
        X[t, :, 7] = M[t - 2] if t >= 2 else 0
        X[t, :, 8] = np.arange(1, 26) / 25          # a própria dezena
        atraso = np.where(M[t] == 1, 0, atraso + 1)
    return X


# ---------------------------------------------------------------- modelos
def zscore(v):
    s = v.std()
    return (v - v.mean()) / (s if s > 0 else 1)


def modelo_composto(X_t):
    """Mesmo critério do lotofacil_estatistica_probabilitica.py (freq/atraso)."""
    return 0.45 * zscore(X_t[:, 4]) + 0.35 * zscore(X_t[:, 5])


def backtest(M, X):
    print("\n=== 2. BACKTEST WALK-FORWARD (concursos "
          f"{INICIO_TESTE+1}..{len(M)}) ===")
    rng = np.random.default_rng(SEMENTE)
    T = len(M)
    testes = range(INICIO_TESTE, T)
    resultados = {k: [] for k in
                  ("Aleatório", "Quentes (freq. 25)", "Frias (atraso)",
                   "Composto (seu método)", "IA Regressão Logística", "IA Gradient Boosting")}
    probs_ia = {"IA Regressão Logística": [], "IA Gradient Boosting": []}
    rotulos = []
    lr = gb = None

    for t in testes:
        if (t - INICIO_TESTE) % RETREINO_A_CADA == 0:
            Xtr = X[100:t].reshape(-1, X.shape[2])
            ytr = M[100:t].reshape(-1)
            lr = LogisticRegression(max_iter=500).fit(Xtr, ytr)
            gb = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05,
                                                random_state=SEMENTE).fit(Xtr, ytr)
        real = M[t]
        scores = {
            "Aleatório": rng.random(25),
            "Quentes (freq. 25)": X[t, :, 2] + rng.random(25) * 1e-6,
            "Frias (atraso)": X[t, :, 5] + rng.random(25) * 1e-6,
            "Composto (seu método)": modelo_composto(X[t]) + rng.random(25) * 1e-6,
            "IA Regressão Logística": lr.predict_proba(X[t])[:, 1],
            "IA Gradient Boosting": gb.predict_proba(X[t])[:, 1],
        }
        for nome, s in scores.items():
            top15 = np.argsort(-s)[:15]
            resultados[nome].append(int(real[top15].sum()))
        for nome in probs_ia:
            probs_ia[nome].extend(scores[nome])
        rotulos.extend(real)

    print(f"{'Modelo':<26}{'média':>7}{'p-valor':>9}{'≥11':>7}{'≥13':>7}{'14':>5}{'15':>5}")
    for nome, ac in resultados.items():
        ac = np.array(ac)
        _, p = stats.ttest_1samp(ac, 9.0)
        print(f"{nome:<26}{ac.mean():7.3f}{p:9.3f}{(ac>=11).mean()*100:6.1f}%"
              f"{(ac>=13).mean()*100:6.2f}%{(ac==14).sum():5d}{(ac==15).sum():5d}")
    print("Teórico (qualquer jogo)      9.000          "
          f"{prob_acertos_min(11)*100:6.1f}%{prob_acertos_min(13)*100:6.2f}%")
    print("\nAUC das IAs (0.5 = chute, 1.0 = previsão perfeita):")
    for nome, p in probs_ia.items():
        print(f"  {nome}: {roc_auc_score(rotulos, p):.4f}")
    return resultados


# ---------------------------------------------------------------- 3. valor esperado
def prob_acertos(k):
    return math.comb(15, k) * math.comb(10, 15 - k) / math.comb(25, 15)


def prob_acertos_min(k):
    return sum(prob_acertos(i) for i in range(k, 16))


def valor_esperado(dados):
    print("\n=== 3. VALOR ESPERADO DA APOSTA ===")
    recentes = [c for c in dados[-200:] if c.get("premiacoes")]
    medias = {}
    for faixa in range(1, 6):
        vals = []
        for c in recentes:
            for pr in c["premiacoes"]:
                if pr["faixa"] == faixa and pr["valorPremio"] > 0:
                    vals.append(pr["valorPremio"])
        medias[16 - faixa] = float(np.mean(vals)) if vals else 0.0
    ev = 0
    for k in range(11, 16):
        contrib = prob_acertos(k) * medias[k]
        ev += contrib
        print(f"  {k} acertos: 1 em {1/prob_acertos(k):>12,.1f}  prêmio médio R$ {medias[k]:>14,.2f}"
              f"  → R$ {contrib:.3f}")
    print(f"Retorno esperado por aposta: R$ {ev:.2f} para R$ {PRECO_APOSTA:.2f} pagos"
          f"  ({ev/PRECO_APOSTA*100:.0f}% de retorno)")
    print("  (prêmios médios já são por ganhador, últimos 200 concursos)")


# ---------------------------------------------------------------- main
def main():
    random.seed(SEMENTE)
    dados = carregar_historico()
    M = matriz_sorteios(dados)
    print(f"Histórico: concursos {dados[0]['concurso']} a {dados[-1]['concurso']}")
    testes_aleatoriedade(M)
    X = construir_features(M)
    backtest(M, X)
    valor_esperado(dados)


if __name__ == "__main__":
    main()

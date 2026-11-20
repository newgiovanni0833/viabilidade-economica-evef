"""Estudo de Viabilidade Econômico-Financeira (EVEF) em três cenários.

Uso:
    python src/modelo.py [premissas.json] [pasta_saida]

O modelo é mensal (para enxergar o vale de caixa da fase de rampa) e os
indicadores são calculados sobre o fluxo de caixa livre anual do projeto,
desalavancado: Ano 0 = investimento + reserva de caixa; Anos 1..N = resultado
operacional após impostos, menos o capex de manutenção.

Só usa a biblioteca padrão do Python.
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Simples Nacional, Anexo III: (limite superior da faixa de RBT12, alíquota nominal, parcela a deduzir)
# Confira a tabela vigente antes de usar o modelo em um caso real.
ANEXO_III = [
    (180_000, 0.060, 0),
    (360_000, 0.112, 9_360),
    (720_000, 0.135, 17_640),
    (1_800_000, 0.160, 35_640),
    (3_600_000, 0.210, 125_640),
    (4_800_000, 0.330, 648_000),
]


# --------------------------------------------------------------------------
# Funções financeiras
# --------------------------------------------------------------------------
def simples_efetiva(rbt12: float) -> float:
    """Alíquota efetiva = (RBT12 × alíquota nominal − parcela a deduzir) ÷ RBT12."""
    if rbt12 <= 0:
        return ANEXO_III[0][1]
    for limite, aliquota, deducao in ANEXO_III:
        if rbt12 <= limite:
            return (rbt12 * aliquota - deducao) / rbt12
    raise ValueError("Receita acima do teto do Simples Nacional (R$ 4,8 milhões)")


def vpl(taxa: float, fluxos: list[float]) -> float:
    return sum(f / (1 + taxa) ** t for t, f in enumerate(fluxos))


def tir(fluxos: list[float], baixo: float = -0.99, alto: float = 10.0) -> float | None:
    """Taxa interna de retorno por bisseção. None se não houver mudança de sinal."""
    f_baixo, f_alto = vpl(baixo, fluxos), vpl(alto, fluxos)
    if f_baixo * f_alto > 0:
        return None
    for _ in range(200):
        meio = (baixo + alto) / 2
        f_meio = vpl(meio, fluxos)
        if abs(f_meio) < 1e-7:
            return meio
        if f_baixo * f_meio < 0:
            alto = meio
        else:
            baixo, f_baixo = meio, f_meio
    return (baixo + alto) / 2


def payback(fluxos: list[float], taxa: float = 0.0) -> float | None:
    """Anos até recuperar o investimento, com interpolação dentro do ano. None se não recupera."""
    acumulado = 0.0
    for t, f in enumerate(fluxos):
        f_desc = f / (1 + taxa) ** t
        if t > 0 and acumulado < 0 <= acumulado + f_desc:
            return (t - 1) + (-acumulado / f_desc)
        acumulado += f_desc
    return None


# --------------------------------------------------------------------------
# Modelo
# --------------------------------------------------------------------------
@dataclass
class Resultado:
    cenario: str
    receita_mensal: list[float] = field(default_factory=list)
    resultado_mensal: list[float] = field(default_factory=list)
    caixa_mensal: list[float] = field(default_factory=list)
    anual: list[dict] = field(default_factory=list)
    fluxos: list[float] = field(default_factory=list)
    indicadores: dict = field(default_factory=dict)


def receita_do_mes(m: int, c: dict) -> float:
    """Rampa linear do mês 1 ao 12; depois, crescimento anual distribuído mês a mês."""
    r1, r12 = c["receita_mes_1"], c["receita_mes_12"]
    if m <= 12:
        return r1 + (r12 - r1) * (m - 1) / 11
    valor = r12
    for mes in range(13, m + 1):
        g = c["crescimento_anual_anos_2_a_5"][(mes - 1) // 12 - 1]
        valor *= (1 + g) ** (1 / 12)
    return valor


def rodar_cenario(nome: str, p: dict) -> Resultado:
    c = p["cenarios"][nome]
    anos = p["horizonte_anos"]
    fixo_base = sum(p["custos_fixos_mensais"].values())
    var_pct = p["custo_variavel_pct_receita"]
    investimento = p["investimento_inicial"] + p["reserva_de_caixa"]

    res = Resultado(nome)
    caixa = p["reserva_de_caixa"]
    aliquota_mes_12 = 0.0

    for ano in range(1, anos + 1):
        fixo = fixo_base * (1 + p["reajuste_anual_custos_fixos"]) ** (ano - 1)
        linha = {"Ano": ano, "Receita": 0.0, "Impostos": 0.0, "Custos variáveis": 0.0, "Custos fixos": 0.0}
        for mes_do_ano in range(1, 13):
            m = (ano - 1) * 12 + mes_do_ano
            receita = receita_do_mes(m, c)
            historico = res.receita_mensal
            if not historico:
                rbt12 = receita * 12                                # empresa nova: receita do mês anualizada
            elif len(historico) < 12:
                rbt12 = sum(historico) / len(historico) * 12        # média dos meses de atividade × 12
            else:
                rbt12 = sum(historico[-12:])
            aliquota = simples_efetiva(rbt12)
            if m == 12:
                aliquota_mes_12 = aliquota
            imposto, variavel = receita * aliquota, receita * var_pct
            resultado = receita - imposto - variavel - fixo
            if mes_do_ano == 12:
                caixa -= p["capex_manutencao_anual"]
            caixa += resultado

            res.receita_mensal.append(receita)
            res.resultado_mensal.append(resultado)
            res.caixa_mensal.append(caixa)
            linha["Receita"] += receita
            linha["Impostos"] += imposto
            linha["Custos variáveis"] += variavel
            linha["Custos fixos"] += fixo

        linha["Resultado operacional"] = linha["Receita"] - linha["Impostos"] - linha["Custos variáveis"] - linha["Custos fixos"]
        linha["Capex de manutenção"] = p["capex_manutencao_anual"]
        linha["Fluxo de caixa livre"] = linha["Resultado operacional"] - linha["Capex de manutenção"]
        linha["Margem operacional"] = linha["Resultado operacional"] / linha["Receita"]
        res.anual.append(linha)

    res.fluxos = [-investimento] + [a["Fluxo de caixa livre"] for a in res.anual]
    tma = p["tma_anual"]
    caixa_min = min(res.caixa_mensal)
    res.indicadores = {
        "Investimento total": investimento,
        "VPL": vpl(tma, res.fluxos),
        "TIR": tir(res.fluxos),
        "Payback simples (anos)": payback(res.fluxos),
        "Payback descontado (anos)": payback(res.fluxos, tma),
        "ROI no horizonte": (sum(res.fluxos[1:]) - investimento) / investimento,
        "Caixa mínimo": caixa_min,
        "Mês do caixa mínimo": res.caixa_mensal.index(caixa_min) + 1,
        "Meses com caixa negativo": sum(1 for x in res.caixa_mensal if x < 0),
        "Primeiro mês com resultado positivo": next((i + 1 for i, r in enumerate(res.resultado_mensal) if r > 0), None),
        "Ponto de equilíbrio mensal (ano 1)": fixo_base / (1 - var_pct - aliquota_mes_12),
    }
    return res


# --------------------------------------------------------------------------
# Saídas
# --------------------------------------------------------------------------
def brl(v: float | None) -> str:
    if v is None:
        return "n/d"
    s = f"{abs(v):,.0f}".replace(",", ".")
    return f"-R$ {s}" if v < 0 else f"R$ {s}"


def pct(v: float | None) -> str:
    return "n/d" if v is None else f"{v * 100:.1f}%".replace(".", ",")


def anos_txt(v: float | None) -> str:
    return "não recupera no horizonte" if v is None else f"{v:.1f} anos ({v * 12:.0f} meses)".replace(".", ",")


def gravar_csv(caminho: Path, cabecalho: list[str], linhas: list[list]) -> None:
    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cabecalho)
        w.writerows(linhas)


def relatorio(p: dict, resultados: list[Resultado]) -> str:
    tma = p["tma_anual"]
    out = [
        f"# Estudo de Viabilidade Econômico-Financeira — {p['empresa']}", "",
        f"{p['descricao']}.", "",
        f"**Horizonte:** {p['horizonte_anos']} anos · **TMA:** {pct(tma)} a.a. · "
        f"**Investimento:** {brl(p['investimento_inicial'])} + reserva de caixa de {brl(p['reserva_de_caixa'])}", "",
        "## Indicadores por cenário", "",
        "| Indicador | " + " | ".join(r.cenario for r in resultados) + " |",
        "|---|" + "---:|" * len(resultados),
    ]
    linhas = [
        ("VPL", lambda i: brl(i["VPL"])),
        ("TIR (a.a.)", lambda i: pct(i["TIR"])),
        ("Payback simples", lambda i: anos_txt(i["Payback simples (anos)"])),
        ("Payback descontado", lambda i: anos_txt(i["Payback descontado (anos)"])),
        ("ROI no horizonte", lambda i: pct(i["ROI no horizonte"])),
        ("Caixa mínimo", lambda i: f"{brl(i['Caixa mínimo'])} (mês {i['Mês do caixa mínimo']})"),
        ("Meses com caixa negativo", lambda i: str(i["Meses com caixa negativo"])),
        ("Primeiro mês com resultado positivo", lambda i: str(i["Primeiro mês com resultado positivo"] or "nenhum")),
        ("Ponto de equilíbrio mensal (ano 1)", lambda i: brl(i["Ponto de equilíbrio mensal (ano 1)"])),
    ]
    for rotulo, fn in linhas:
        out.append(f"| {rotulo} | " + " | ".join(fn(r.indicadores) for r in resultados) + " |")

    for r in resultados:
        out += ["", f"## Fluxo anual — cenário {r.cenario}", "",
                "| Ano | Receita | Impostos | Custos variáveis | Custos fixos | Resultado operacional | Margem | Fluxo de caixa livre |",
                "|---:|---:|---:|---:|---:|---:|---:|---:|",
                f"| 0 | | | | | | | {brl(r.fluxos[0])} |"]
        for a in r.anual:
            out.append(f"| {a['Ano']} | {brl(a['Receita'])} | {brl(a['Impostos'])} | {brl(a['Custos variáveis'])} | "
                       f"{brl(a['Custos fixos'])} | {brl(a['Resultado operacional'])} | {pct(a['Margem operacional'])} | "
                       f"{brl(a['Fluxo de caixa livre'])} |")

    out += ["", "## Leitura dos resultados", ""]
    for r in resultados:
        i = r.indicadores
        veredito = "cria valor" if i["VPL"] > 0 else "destrói valor"
        frase = f"- **{r.cenario}:** o projeto {veredito} à TMA de {pct(tma)} (VPL de {brl(i['VPL'])})."
        n = i["Meses com caixa negativo"]
        if i["Primeiro mês com resultado positivo"] is None:
            frase += " A operação não gera resultado mensal positivo em nenhum mês do horizonte."
        elif n:
            frase += (f" A reserva não cobre a fase de rampa: o caixa fica negativo por {n} {'mês' if n == 1 else 'meses'} "
                      f"e chega a {brl(i['Caixa mínimo'])} no mês {i['Mês do caixa mínimo']}.")
        else:
            frase += f" A reserva cobre a fase de rampa (caixa mínimo de {brl(i['Caixa mínimo'])} no mês {i['Mês do caixa mínimo']})."
        out.append(frase)
    return "\n".join(out) + "\n"


def main(arq_premissas: Path, saida: Path) -> list[Resultado]:
    p = json.loads(arq_premissas.read_text(encoding="utf-8"))
    resultados = [rodar_cenario(nome, p) for nome in p["cenarios"]]
    saida.mkdir(parents=True, exist_ok=True)

    colunas = ["Receita", "Impostos", "Custos variáveis", "Custos fixos", "Resultado operacional",
               "Capex de manutenção", "Fluxo de caixa livre"]
    gravar_csv(saida / "fluxo_anual.csv", ["Cenário", "Ano"] + colunas,
               [[r.cenario, a["Ano"]] + [f"{a[c]:.2f}".replace(".", ",") for c in colunas] for r in resultados for a in r.anual])
    gravar_csv(saida / "caixa_mensal.csv", ["Cenário", "Mês", "Receita", "Resultado", "Caixa acumulado"],
               [[r.cenario, m + 1] + [f"{v:.2f}".replace(".", ",") for v in (r.receita_mensal[m], r.resultado_mensal[m], r.caixa_mensal[m])]
                for r in resultados for m in range(len(r.caixa_mensal))])
    (saida / "relatorio.md").write_text(relatorio(p, resultados), encoding="utf-8")

    for r in resultados:
        i = r.indicadores
        print(f"{r.cenario:<11} VPL {brl(i['VPL']):>12} | TIR {pct(i['TIR']):>7} | "
              f"payback desc. {anos_txt(i['Payback descontado (anos)'])} | caixa mín. {brl(i['Caixa mínimo'])} (mês {i['Mês do caixa mínimo']})")
    print(f"Saídas gravadas em {saida}/")
    return resultados


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parents[1]
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else raiz / "premissas" / "premissas.json",
         Path(sys.argv[2]) if len(sys.argv) > 2 else raiz / "saida")

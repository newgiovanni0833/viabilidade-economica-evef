import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import modelo  # noqa: E402


def test_simples_primeira_faixa():
    assert modelo.simples_efetiva(100_000) == pytest.approx(0.06)
    assert modelo.simples_efetiva(180_000) == pytest.approx(0.06)


def test_simples_segunda_faixa():
    # (360.000 × 11,2% − 9.360) ÷ 360.000 = 8,6%
    assert modelo.simples_efetiva(360_000) == pytest.approx(0.086)


def test_simples_e_continua_entre_faixas():
    assert modelo.simples_efetiva(180_000.01) == pytest.approx(0.06, abs=1e-6)
    assert modelo.simples_efetiva(360_000.01) == pytest.approx(0.086, abs=1e-6)


def test_simples_acima_do_teto():
    with pytest.raises(ValueError):
        modelo.simples_efetiva(5_000_000)


def test_vpl_e_tir_caso_conhecido():
    fluxos = [-1000, 500, 500, 500]
    assert modelo.vpl(0.10, fluxos) == pytest.approx(243.43, abs=0.01)
    assert modelo.tir(fluxos) == pytest.approx(0.2338, abs=1e-4)
    assert modelo.vpl(modelo.tir(fluxos), fluxos) == pytest.approx(0, abs=1e-3)


def test_tir_sem_mudanca_de_sinal():
    assert modelo.tir([-100, -50, -10]) is None


def test_payback_interpolado():
    assert modelo.payback([-1000, 400, 400, 400]) == pytest.approx(2.5)
    assert modelo.payback([-1000, 100, 100]) is None
    assert modelo.payback([-1000, 500, 500, 500], 0.10) == pytest.approx(2.35, abs=0.01)


def test_rampa_de_receita():
    c = {"receita_mes_1": 1000, "receita_mes_12": 12000, "crescimento_anual_anos_2_a_5": [0.10, 0, 0, 0]}
    assert modelo.receita_do_mes(1, c) == 1000
    assert modelo.receita_do_mes(12, c) == 12000
    assert modelo.receita_do_mes(24, c) == pytest.approx(13200)
    assert modelo.receita_do_mes(36, c) == pytest.approx(13200)


def test_cenarios_ordenados_e_coerentes():
    p = json.loads((RAIZ / "premissas" / "premissas.json").read_text(encoding="utf-8"))
    r = {n: modelo.rodar_cenario(n, p) for n in p["cenarios"]}
    vpls = [r[n].indicadores["VPL"] for n in ("Pessimista", "Realista", "Otimista")]
    assert vpls == sorted(vpls)
    for res in r.values():
        # fluxo anual = soma dos resultados mensais − capex
        for i, ano in enumerate(res.anual):
            soma = sum(res.resultado_mensal[i * 12:(i + 1) * 12])
            assert ano["Fluxo de caixa livre"] == pytest.approx(soma - p["capex_manutencao_anual"])
        # caixa final = reserva + soma dos fluxos livres
        assert res.caixa_mensal[-1] == pytest.approx(p["reserva_de_caixa"] + sum(res.fluxos[1:]))

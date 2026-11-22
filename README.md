# 💰 Estudo de Viabilidade Econômico-Financeira (EVEF)

Modelo financeiro em três cenários para decidir se um novo negócio se paga: VPL, TIR, Payback, ROI, ponto de equilíbrio e, principalmente, o **vale de caixa** da fase de rampa.

> ⚠️ **Dados fictícios.** O "Estúdio Aurora" e todas as premissas são inventados. A estrutura do modelo é a que aplico em estudos reais para pequenos negócios.

## 🎯 Problema de negócio

Quem abre um negócio costuma perguntar "em quanto tempo isso se paga?". A pergunta que quebra empresas é outra: **"o caixa aguenta até lá?"**. Um projeto pode ter VPL positivo e, mesmo assim, ficar sem dinheiro no sexto mês.

Por isso o modelo é **mensal** na operação e **anual** nos indicadores:

- o fluxo mensal mostra a rampa de receita, o mês de virada e o caixa mínimo;
- o fluxo anual alimenta VPL, TIR e Payback.

## 🧮 Metodologia

| Elemento | Como é tratado |
|---|---|
| Fluxo de caixa | Livre e desalavancado: Ano 0 = investimento + reserva; demais anos = resultado operacional após impostos − capex de manutenção |
| Receita | Rampa linear do mês 1 ao 12; depois, crescimento anual por cenário |
| Tributos | **Alíquota efetiva progressiva do Simples Nacional (Anexo III)**, recalculada mês a mês sobre a receita dos últimos 12 meses |
| Custos fixos | Lista detalhada, com reajuste anual. Inclui o pró-labore dos sócios |
| Custos variáveis | Percentual da receita |
| Indicadores | VPL, TIR, Payback simples e descontado, ROI, ponto de equilíbrio, caixa mínimo e mês em que ocorre |
| Cenários | Pessimista, Realista e Otimista, definidos pela velocidade da rampa |

Usar a alíquota efetiva progressiva, em vez de um valor fixo de imposto, evita subestimar a carga tributária quando o faturamento cresce.

## ▶️ Como executar

Requer apenas Python 3.9+ (biblioteca padrão).

```bash
python src/modelo.py
```

Para testar outro negócio, edite [`premissas/premissas.json`](premissas/premissas.json). Todas as entradas ficam nesse arquivo; nenhum número está escrito no código.

Saídas em `saida/`:

- `relatorio.md`: indicadores, fluxo anual e leitura de cada cenário
- `fluxo_anual.csv` e `caixa_mensal.csv`: prontos para Excel ou Power BI

## 📊 Resultado da demonstração

Investimento de R$ 70 mil + reserva de R$ 15 mil · horizonte de 5 anos · TMA de 20% a.a.

| Indicador | Pessimista | Realista | Otimista |
|---|---:|---:|---:|
| VPL | −R$ 166.307 | R$ 85.848 | R$ 330.080 |
| TIR (a.a.) | n/d | 47,7% | 110,7% |
| Payback descontado | não recupera | 35 meses | 18 meses |
| Caixa mínimo | −R$ 113.280 (mês 60) | −R$ 262 (mês 6) | R$ 9.382 (mês 3) |
| Primeiro mês com resultado positivo | nenhum | 7 | 4 |

**O que o modelo revela:**

1. **O risco é comercial, e não de capital.** A diferença entre destruir R$ 166 mil e criar R$ 86 mil de valor está inteiramente na velocidade da rampa de receita.
2. **O cenário realista é viável, mas a reserva é insuficiente por pouco.** O caixa fica levemente negativo no sexto mês (−R$ 262), e qualquer atraso na rampa aumenta a necessidade de aporte.
3. **O ponto de equilíbrio é de cerca de R$ 12,8 mil por mês.** Essa é a meta que precisa ser vigiada mês a mês.

Relatório completo em [saida/relatorio.md](saida/relatorio.md).

## ✅ Testes

```bash
pip install pytest
pytest -q
```

Os testes conferem a alíquota efetiva em cada faixa (inclusive a continuidade entre faixas), VPL e TIR contra casos conhecidos, o payback interpolado, a rampa de receita e a coerência entre o fluxo mensal e o anual.

## ⚠️ Limites do modelo

- A tabela do Simples Nacional está escrita no código: confira a tabela vigente antes de aplicar a um caso real.
- O modelo não trata o Fator R (migração entre Anexo III e Anexo V), financiamento, depreciação nem capital de giro por prazo de recebimento.
- Os cenários são determinísticos. Não há simulação probabilística.

## 🛠️ Tecnologias e metodologias

Python · fluxo de caixa descontado · análise de cenários · Simples Nacional · pytest

## 👤 Autor

**Newton Giovanni** · Economista (CORECON-MT nº 02151) · [LinkedIn](https://www.linkedin.com/in/newton-giovanni/) · [Portfólio](https://github.com/newgiovanni0833)

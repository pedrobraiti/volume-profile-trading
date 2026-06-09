# volume-profile-trading

Backtesting quantitativo da estratégia **Volume Profile / Market Profile** (Steidlmayer/Dalton):
implementa as regras objetivas (Regra dos 80%, fade de extremos / reversão ao POC, signal candle
edge-to-edge) e mede **expectância após custos** em dados históricos, comparando parâmetros
conservadores vs. agressivos. Entrega final: um relatório PDF técnico com gráficos e tabelas.

## Como rodar
_A preencher quando houver código executável._

## Stack
- Python 3.12+ (venv em `.venv`)
- Dados: `yfinance` (Yahoo Finance) e/ou outra fonte gratuita confiável
- Análise: `pandas`, `numpy`
- Gráficos / PDF: `matplotlib`, `reportlab` (a confirmar)

## Documento de referência
`volume-profile-estrategia.md` — explica a estratégia, a matemática (Value Area 70%, POC, HVN/LVN),
os day-types e a avaliação crítica (o que é sólido vs. folclore).

> **Aviso:** projeto educativo / de pesquisa. Não é recomendação de investimento.

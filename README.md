# volume-profile-trading

Backtesting quantitativo da estratégia **Volume Profile / Market Profile** (Steidlmayer/Dalton):
implementa as regras objetivas (Reversão ao POC, Edge-to-Edge, Breakout da Value Area, Exaustão de
volume e a Regra dos 80%), mede **expectância após custos** em até 33 anos de dados e valida tudo
**out-of-sample** (walk-forward). Entrega final: um relatório PDF técnico com 16 páginas, 15
figuras e 7 tabelas.

## Principais achados

- Existe um **edge real, porém modesto, na ponta comprada de índices líquidos** (SPY, QQQ) que
  **sobrevive out-of-sample** (Profit Factor 1,4–2,1). Falha nas ações brasileiras tendenciais.
- A **leitura de volume** (exaustão / "sem oferta" e absorção no fundo) é mais robusta que o perfil
  puro. O **signal candle** (confirmação por volume) eleva o PF do QQQ de 1,1 para 1,9.
- Duas "lendas" **não se sustentam**: a Regra dos 80% não atravessa 80% (e perde após custos na
  amostra recente) e os day-types não preveem continuação (se algo, revertem).
- Como sistema isolado **não bate buy & hold em retorno** (baixa exposição), mas entrega um fluxo
  muito mais suave: portfólio diversificado com Sharpe ~0,5 e drawdown máximo de ~7%.

## Como rodar

```powershell
# 1. Ambiente (Python 3.12+)
py -3.12 -m venv .venv
& ".venv\Scripts\Activate.ps1"          # se bloquear: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pip install -r requirements.txt
pip install -e .

# 2. Testes
pytest -q

# 3. Rodar todos os experimentos (baixa/cacheia dados, ~1 min) -> output/results.pkl
python scripts/run_experiments.py

# 4. Gerar figuras + relatório PDF -> output/relatorio_volume_profile.pdf
python scripts/build_report.py
```

Os dados são baixados do Yahoo Finance e cacheados em `data/cache/` (Parquet). As saídas
(figuras, PDF, CSVs) vão para `output/` (não versionado).

## Estrutura

```
src/vptrading/
  data/         download + cache de OHLCV (yfinance)
  core/         Volume Profile (POC, Value Area 70%, HVN/LVN), composite, day-types
  strategies/   Reversão ao POC, Edge-to-Edge, Breakout, Exaustão de volume, Regra dos 80%
  backtest/     modelos de custo (US/BR), métricas (expectância, Sharpe, etc.), engine event-driven
  optimization/ grid search + walk-forward (in-sample -> out-of-sample)
  analysis/     estudos das afirmações (day-types, divergência, absorção, regra 80%)
  reporting/    geração de gráficos (matplotlib) e do PDF (reportlab)
scripts/        run_experiments.py, build_report.py
tests/          testes do núcleo (Value Area, métricas, engine)
```

## Stack
- Python 3.12 (venv em `.venv`)
- `yfinance` (dados), `pandas`/`numpy`/`scipy` (análise), `matplotlib` (gráficos), `reportlab` (PDF)

## Documento de referência
`volume-profile-estrategia.md` — a estratégia, a matemática (Value Area 70%, POC, HVN/LVN), os
day-types e a avaliação crítica (o que é sólido vs. folclore).

> **Aviso:** projeto educativo / de pesquisa. Não é recomendação de investimento.

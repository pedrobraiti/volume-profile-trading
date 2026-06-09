# Contexto do projeto

> Camada **estável** da memória: o que o projeto é e suas características macro. Muda devagar.
> O detalhe volátil de "de onde parei" fica no `handoff.md`; as tarefas, no `todo.md`;
> as decisões com o porquê, no `decisions.md`.

**Nome:** volume-profile-trading
**Descrição:** Backtesting quantitativo da estratégia Volume Profile / Market Profile (Steidlmayer/Dalton) para descobrir, com dados históricos, quais parâmetros têm expectância positiva após custos.
**Stack:** Python 3.12+ (venv `.venv`); dados via `yfinance` (Yahoo Finance) e/ou outra fonte gratuita confiável; análise com `pandas`/`numpy`; gráficos com `matplotlib`; PDF técnico via `reportlab`/`matplotlib` (a definir).

## Visão geral
A partir do documento de referência `volume-profile-estrategia.md`, o projeto implementa e
testa as regras objetivas da estratégia (Regra dos 80%, fade de extremos / reversão ao POC,
edge-to-edge via signal candle, day-types D/P/b/Trend). O objetivo final é medir **expectância
após custos** ao longo de muitos trades e anos, comparar parâmetros conservadores vs. agressivos,
e entregar um **relatório PDF profissional** com gráficos, tabelas e comparações.

## Fase atual
Setup inicial + definição de escopo (fonte de dados, instrumentos, regras a testar).
Aguardando respostas do usuário às perguntas de escopo antes de iniciar a implementação autônoma.

## Restrições e bloqueios de longo prazo
- **Volume Profile é, na origem, uma estratégia INTRADAY** (blocos de 30 min, Initial Balance,
  aceitação em 2 TPOs). Dados intraday gratuitos têm histórico curto: Yahoo entrega ~60 dias de
  30 min e ~730 dias de 1h. **Não é possível** um backtest intraday fiel de 20 anos com dados
  gratuitos. Isso obriga uma decisão de escopo (ver `decisions.md` / `todo.md`).
- Volume Profile **não é preditivo** (até os fornecedores dizem isso). O backtest mede edge real,
  não confirma a narrativa do vídeo.
- Day trade de varejo tem base rate negativa (97% perdem — Chague/De-Losso, USP/FGV). O relatório
  deve ser honesto sobre isso.

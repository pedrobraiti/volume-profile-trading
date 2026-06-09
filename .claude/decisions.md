# Decisões arquiteturais/técnicas

Registro de decisões com o "porquê". Append-only — não edita entradas antigas.

<!-- Formato:
## YYYY-MM-DD — Título curto da decisão
**Motivo:** por que foi decidido assim.
**Alternativas consideradas:** o que ficou de fora e por quê.
-->

## 2026-06-09 — Linguagem e stack base: Python 3.12+ com yfinance/pandas/matplotlib
**Motivo:** ecossistema maduro para dados financeiros e backtesting; `yfinance` é gratuito e
confiável para OHLCV diário com longo histórico; `pandas`/`numpy` para vetorização; `matplotlib`
para os gráficos do PDF.
**Alternativas consideradas:** bibliotecas de backtest prontas (`backtrader`, `vectorbt`,
`backtesting.py`) — podem entrar depois, mas a lógica de Volume Profile (POC/VA/HVN/LVN, 80% rule)
é específica e provavelmente será implementada à mão para controle total e transparência no relatório.

## 2026-06-09 — Conflito fundamental: estratégia intraday vs. backtest de 20 anos
**Motivo:** registrar a restrição-chave antes de decidir o escopo. A estratégia original é
intraday (30 min). Fontes gratuitas não dão 20 anos de intraday. Caminhos possíveis:
  (A) **Composite Volume Profile diário** — perfil de volume-por-preço numa janela móvel de N
      dias usando barras diárias; permite 20+ anos com Yahoo; testa reversão ao POC e edge-to-edge
      adaptados a swing. Fiel ao *conceito*, não ao timeframe.
  (B) **Intraday 30 min fiel** (Regra dos 80%, day types, IB) — limitado a ~60 dias (Yahoo) ou
      ~1-2 anos com provedor intraday gratuito; amostra menor.
  (C) **Híbrido** — backtest diário longo (robustez estatística) + validação intraday recente.
**Alternativas consideradas:** comprar dados intraday históricos (Databento/Polygon) — fora do
escopo gratuito pedido. **Decisão final pendente de resposta do usuário.**

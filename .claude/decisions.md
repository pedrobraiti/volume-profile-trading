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
escopo gratuito pedido.

## 2026-06-09 — Escopo definido pelo usuário: Híbrido + Mix US/Brasil
**Motivo:** o usuário escolheu (C) abordagem **híbrida** — backtest diário longo (~20+ anos) com
Composite Volume Profile em janela móvel para robustez estatística, MAIS uma validação intraday
recente (~60 dias, 30 min) para a Regra dos 80% e os day-types. Instrumentos: **Mix US + Brasil**
(SPY, QQQ no US; PETR4, VALE3, BOVA11 no Brasil) para comparar mercado maduro vs. emergente.
**Alternativas consideradas:** só-diário (perde a Regra dos 80% fiel) e só-intraday (amostra curta)
— ambos rejeitados em favor do híbrido. Só-US (mais limpo) preterido para incluir relevância ao
mercado do usuário.

## 2026-06-09 — Premissas de custo e capital (defaults, ajustáveis)
**Motivo:** registrar as premissas que adotarei por padrão no engine, todas documentadas no PDF e
fáceis de variar:
  - Capital inicial: US$ 100.000 (e R$ 100.000 para B3), sem alavancagem no caso-base.
  - Sizing: risco fixo por trade (ex.: 1% do capital no stop) — testar também all-in/fração fixa.
  - Custos US: ~US$0 corretagem (ETF) + slippage 1-2 ticks + spread modelado.
  - Custos B3: corretagem ~R$0 (varejo atual) + emolumentos B3 + slippage; modelar realisticamente.
  - Métrica-rainha: **expectância após custos** + retorno/risco (Sharpe, Sortino, max drawdown,
    profit factor, win rate, payoff). Comparar conservador vs. agressivo.
**Alternativas consideradas:** alavancagem de mini-contratos (WIN/ES) — fica como cenário extra,
não como base, por adicionar risco de ruína difícil de comparar entre mercados.

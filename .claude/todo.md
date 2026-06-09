# TODO

Plano vivo do projeto. Tarefas e subtarefas, marcadas conforme concluídas.

**Escopo travado:** Híbrido (diário ~20+ anos + intraday recente ~60d/30min). Instrumentos:
SPY, QQQ (US) + PETR4, VALE3, BOVA11 (B3). Métrica-rainha: expectância após custos.

## Em progresso
- [ ] Montar `.venv` e `requirements.txt` (yfinance, pandas, numpy, matplotlib, reportlab, etc.)

## Próximas
- [ ] Módulo de ingestão de dados (download + cache local Parquet de OHLCV; diário + 30min)
- [ ] Núcleo Volume Profile: POC, Value Area (algoritmo 70%), HVN/LVN, composite em janela móvel
- [ ] Detector de day-type (D / P / b / Trend Day) e filtro de tendência
- [ ] Implementar regras de trade objetivas:
  - [ ] Regra dos 80% (intraday: abre fora da VA → reentra/aceita 2 períodos → alvo borda oposta)
  - [ ] Fade de extremos / reversão ao POC (day types D/P/b)
  - [ ] Signal candle edge-to-edge
- [ ] Engine de backtest com custos (corretagem/emolumentos/spread/slippage) e sizing por risco
- [ ] Métricas: expectância, Sharpe, Sortino, max drawdown, profit factor, payoff, win rate
- [ ] Varredura de parâmetros (grid): janela do perfil, % da VA, stops/alvos, filtros de tendência
- [ ] Análise: conservador vs. agressivo; tabelas comparativas por instrumento e mercado
- [ ] Geração do relatório PDF profissional (gráficos, tabelas, comparações)

## Concluído
- [x] Setup inicial do projeto
- [x] Leitura e compreensão de `volume-profile-estrategia.md`
- [x] Definir escopo com o usuário (híbrido; mix US+Brasil; repo privado no GitHub)
- [x] Criar repositório privado no GitHub e push inicial

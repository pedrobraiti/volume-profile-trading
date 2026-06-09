# TODO

Plano vivo do projeto. Tarefas e subtarefas, marcadas conforme concluídas.

## Em progresso
- [ ] Definir escopo com o usuário (fonte de dados, instrumentos, timeframe, regras a testar)

## Próximas
- [ ] Montar `.venv` e `requirements.txt` (yfinance, pandas, numpy, matplotlib, etc.)
- [ ] Módulo de ingestão de dados (download + cache local de OHLCV)
- [ ] Núcleo Volume Profile: cálculo de POC, Value Area (algoritmo 70%), HVN/LVN
- [ ] Implementar regras de trade objetivas:
  - [ ] Regra dos 80% (abre fora da VA → reentra/aceita → alvo borda oposta)
  - [ ] Fade de extremos / reversão ao POC (day types D/P/b)
  - [ ] Signal candle edge-to-edge
- [ ] Engine de backtest com custos (spread/corretagem/slippage) e métricas de expectância
- [ ] Varredura de parâmetros (grid): janela do perfil, % da VA, stops/alvos, filtros de tendência
- [ ] Análise dos resultados: conservador vs. agressivo; tabelas comparativas
- [ ] Geração do relatório PDF profissional (gráficos, tabelas, comparações)

## Concluído
- [x] Setup inicial do projeto
- [x] Leitura e compreensão de `volume-profile-estrategia.md`

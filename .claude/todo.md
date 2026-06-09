# TODO

Plano vivo do projeto. Tarefas e subtarefas, marcadas conforme concluídas.

**Escopo travado:** Híbrido (diário ~20+ anos + intraday recente ~60d/30min). Instrumentos:
SPY, QQQ (US) + PETR4, VALE3, BOVA11 (B3). Métrica-rainha: expectância após custos.

## Em progresso
- (nada — primeira entrega completa)

## Próximas (ideias de evolução, se o usuário quiser)
- [ ] Dados intraday históricos pagos para testar a Regra dos 80% com amostra grande
- [ ] Sleeve combinado otimizado (ex.: Exaustão + signal candle) por instrumento
- [ ] Mais classes de ativos (cripto tem anos de 30min grátis → testar intraday fiel)
- [ ] Custos/sizing mais granulares por instrumento

## Concluído
- [x] Setup inicial do projeto
- [x] Leitura e compreensão de `volume-profile-estrategia.md`
- [x] Definir escopo com o usuário (híbrido; mix US+Brasil; repo privado no GitHub)
- [x] Criar repositório privado no GitHub e push inicial
- [x] `.venv` + `requirements.txt` (yfinance, pandas, numpy, scipy, matplotlib, reportlab, pyarrow)
- [x] Módulo de ingestão de dados (download + cache Parquet; diário 33 anos + 30min recente)
- [x] Núcleo Volume Profile: POC, Value Area (algoritmo 70%), HVN/LVN, composite em janela móvel
- [x] Detector de day-type (D/P/b/Trend) e filtro de tendência
- [x] Estratégias: Reversão ao POC, Edge-to-Edge, Breakout, Exaustão de volume, Regra dos 80%
- [x] Engine event-driven com custos US/BR e sizing por risco
- [x] Métricas: expectância, Sharpe, Sortino, max drawdown, profit factor, payoff, win rate
- [x] Grid de parâmetros + **walk-forward OOS** (testes posteriores a partir do passado)
- [x] Estudos das afirmações: day-types, divergência, absorção, Regra dos 80% (§4.3/§6/§7)
- [x] Portfólio diversificado + eixo conservador/agressivo (sizing e alavancagem)
- [x] 15 figuras profissionais (inspecionadas visualmente) + relatório PDF de 16 páginas
- [x] 9 testes unitários passando; README e memória atualizados

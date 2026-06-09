"""vptrading — backtesting da estratégia Volume Profile / Market Profile.

Pacote modular organizado por domínio:
- data:         ingestão e cache de dados de mercado (OHLCV).
- core:         matemática do Volume Profile (POC, Value Area, HVN/LVN) e day-types.
- strategies:   regras de trade objetivas derivadas da estratégia.
- backtest:     engine de simulação, modelos de custo e métricas de performance.
- optimization: grid search e validação walk-forward (in-sample / out-of-sample).
- reporting:    gráficos e geração do relatório PDF.
"""

__version__ = "0.1.0"

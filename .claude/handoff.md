# Handoff — de onde parei

> **Propósito:** este arquivo serve para que um chat NOVO saiba com precisão "de onde eu parei",
> de forma relativamente detalhada. É o PRIMEIRO arquivo que a próxima sessão lê.
> Mantenha-o vivo e específico — detalhado o bastante para retomar sem reconstruir o raciocínio.

**Última atualização:** 2026-06-09 — setup concluído, escopo travado, repo no GitHub

## Onde parei
`/setup` concluído: estrutura `.claude/`, `CLAUDE.md`, `README.md`, git init, commit inicial e
**repo privado criado/pushado** em https://github.com/pedrobraiti/volume-profile-trading.
Li e entendi por completo o `volume-profile-estrategia.md`. O usuário respondeu às perguntas de
escopo: **(1) abordagem Híbrida**, **(2) Mix US + Brasil**, **(3) criar repo privado** (feito).

## Contexto mental
Escopo travado (ver `decisions.md`): backtest DIÁRIO de ~20+ anos com Composite Volume Profile em
janela móvel (robustez) + validação INTRADAY recente (~60d, 30min) para Regra dos 80% e day-types.
Instrumentos: SPY, QQQ (US) + PETR4, VALE3, BOVA11 (B3). Métrica-rainha: **expectância após custos**.
Premissas de custo/capital definidas como defaults ajustáveis (ver `decisions.md`). Apresentei o
plano ao usuário com as premissas; ele tinha dito "por ora apenas prepare o /setup", então estou
aguardando o "go" final (ou ele já autorizou seguir autônomo — confirmar na próxima mensagem).

## Próximo passo concreto
Ao receber o "go": criar `.venv` (Python 3.12 se houver atrito com 3.14), `requirements.txt`
(yfinance, pandas, numpy, matplotlib, reportlab, pyarrow), e implementar o módulo de ingestão de
dados (`data/`) com cache Parquet — baixar diário longo de SPY/QQQ/PETR4/VALE3/BOVA11 e 30min
recente. Validar qualidade/volume de cada série antes de seguir.

## Em aberto / armadilhas
- Yahoo: volume confiável para ETFs/ações US (SPY, QQQ); volume de índices (^BVSP, ^GSPC) e de
  futuros contínuos é menos confiável / mais curto. Preferir ETFs para o perfil de volume.
- "Taxa de acerto ≠ lucro": o relatório PRECISA medir expectância após custos, não win rate.
- Trend Day quebra todas as táticas de fade — incluir filtro/detecção de tendência no backtest.
- Python 3.14.2 está instalado; usar venv. Evitar libs que ainda não suportem 3.14 — se houver
  atrito, criar venv com 3.12.

## Como retomar rápido
- Referência da estratégia: `volume-profile-estrategia.md` (raiz).
- Escopo e restrições: `.claude/context.md`, `.claude/decisions.md`.
- Plano: `.claude/todo.md`.
- Ainda não há código nem `.venv`.

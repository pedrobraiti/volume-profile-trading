# Handoff — de onde parei

> **Propósito:** este arquivo serve para que um chat NOVO saiba com precisão "de onde eu parei",
> de forma relativamente detalhada. É o PRIMEIRO arquivo que a próxima sessão lê.
> Mantenha-o vivo e específico — detalhado o bastante para retomar sem reconstruir o raciocínio.

**Última atualização:** 2026-06-09 — setup inicial

## Onde parei
Acabei de rodar o `/setup`: criei a estrutura `.claude/`, `CLAUDE.md`, `README.md`, git init e
commit inicial. Li e entendi por completo o `volume-profile-estrategia.md` (estratégia Volume
Profile / Market Profile). O usuário pediu: backtest de vários anos (~20) com dados gratuitos
(Yahoo Finance), análise dos melhores parâmetros (conservadores e agressivos) e um **relatório
PDF profissional** ao final. Ele autorizou seguir de forma autônoma quando eu julgar pronto,
mas pediu que **por ora** eu apenas prepare o setup e faça as perguntas necessárias.

## Contexto mental
A grande questão técnica: a estratégia é **intraday por natureza** (TPO de 30 min, IB, aceitação
em 2 períodos, Regra dos 80%). Yahoo NÃO tem 20 anos de intraday (só ~60 dias de 30 min). Então
um backtest fiel de 20 anos é impossível com dados gratuitos. A saída é decidir entre:
(A) Composite Volume Profile diário (20+ anos, swing), (B) intraday fiel mas amostra curta,
(C) híbrido. Recomendo o híbrido com ênfase em (A) para a robustez de 20 anos. Também preciso
definir instrumento (recomendo SPY/QQQ por terem o volume diário mais limpo e longo).
Fiz as perguntas de escopo ao usuário via AskUserQuestion.

## Próximo passo concreto
Aguardar as respostas do usuário às 3 perguntas de escopo (abordagem de dados/timeframe,
instrumentos, regras a priorizar). Assim que responder, atualizar `decisions.md` com a escolha,
montar `.venv` + `requirements.txt` e começar o módulo de ingestão de dados.

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

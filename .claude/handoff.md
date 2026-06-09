# Handoff — de onde parei

> **Propósito:** este arquivo serve para que um chat NOVO saiba com precisão "de onde eu parei",
> de forma relativamente detalhada. É o PRIMEIRO arquivo que a próxima sessão lê.
> Mantenha-o vivo e específico — detalhado o bastante para retomar sem reconstruir o raciocínio.

**Última atualização:** 2026-06-09 — projeto COMPLETO (1ª entrega: código + relatório PDF)

## Onde parei
Entreguei o projeto inteiro de ponta a ponta: pipeline de backtesting funcional + **relatório PDF
de 16 páginas** (`output/relatorio_volume_profile.pdf`). Todos os experimentos rodam em ~1 min via
`scripts/run_experiments.py` (gera `output/results.pkl`); o PDF e as 15 figuras saem de
`scripts/build_report.py`. 9 testes passando. Tudo commitado e pushado no GitHub.

## Contexto mental
A estratégia foi adaptada para o conflito intraday-vs-20-anos via abordagem híbrida (diário longo
com Composite Volume Profile + intraday recente para a Regra dos 80%). Implementei 4 estratégias
diárias (REV, E2E, BRK, EXH) + Regra dos 80% intraday, engine event-driven com custos, e — o que o
usuário mais pediu — **validação walk-forward (IS->OOS)** para evitar overfitting.

**Achados centrais (todos no PDF):** edge real mas modesto na ponta comprada de índices líquidos
(SPY/QQQ) que sobrevive OOS (PF 1,4–2,1); falha em ações BR tendenciais; a leitura de volume
(exaustão/absorção no fundo) é a tática mais robusta; signal candle eleva PF do QQQ de 1,1→1,9;
Regra dos 80% e day-types NÃO se sustentam; como sistema isolado não bate buy&hold em retorno mas
tem drawdown muito menor. Revisei o documento §por§ e cobri inclusive absorção (§6), signal candle
(§7) e resolução (§4.3) em "Estudos complementares".

Inspecionei visualmente TODAS as 15 figuras PNG (via Read) e as páginas do PDF (renderizadas com
PyMuPDF em `output/_pdfpreview/`), ajustando títulos, colormaps e seleção de exemplos.

## Próximo passo concreto
Projeto entregue. Se o usuário quiser evoluir: (a) dados intraday históricos pagos para testar a
Regra dos 80% com amostra grande; (b) custos/sizing mais realistas por instrumento; (c) mais
instrumentos/classes (cripto tem anos de 30min grátis); (d) combinar sinais (ex.: EXH + signal
candle) num sleeve único otimizado; (e) revisar texto do PDF se quiser outro tom.

## Em aberto / armadilhas
- `output/` e `data/cache/` são gitignored (artefatos gerados). O PDF está no disco local, não no
  git. Para regerar: rodar os 2 scripts.
- yfinance 0.2.51 quebrou (Yahoo mudou API); subi para 1.4.1 — manter atualizado.
- PyMuPDF (`fitz`) foi instalado só para QA visual do PDF; não está no requirements.txt (não é
  necessário para gerar a entrega).
- max_leverage no engine é um TETO, não multiplicador — alavancagem real vem de risk_per_trade ou
  de escalar os retornos do portfólio (ver flagship/portfolio no orquestrador).
- Amostra da Regra dos 80% é minúscula (~60 dias de 30min) — conclusões só indicativas.

## Como retomar rápido
- Relatório: `output/relatorio_volume_profile.pdf`. Resultados: `output/results.pkl`.
- Rodar: `python scripts/run_experiments.py` depois `python scripts/build_report.py`.
- Código: `src/vptrading/` (data, core, strategies, backtest, optimization, analysis, reporting).
- Achados e decisões: `.claude/decisions.md`; estratégia: `volume-profile-estrategia.md`.

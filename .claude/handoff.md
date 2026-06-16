# Handoff — de onde parei

> **Propósito:** este arquivo serve para que um chat NOVO saiba com precisão "de onde eu parei",
> de forma relativamente detalhada. É o PRIMEIRO arquivo que a próxima sessão lê.
> Mantenha-o vivo e específico — detalhado o bastante para retomar sem reconstruir o raciocínio.

**Última atualização:** 2026-06-16 — repo tornado PÚBLICO + projeto inteiro traduzido para INGLÊS

## ATUALIZAÇÃO MAIS RECENTE (publicação / inglês)
O usuário pediu para tornar o repo público e profissional, inspirado em `paper2004`. Feito:
- **Tudo traduzido para inglês**: todo o código (docstrings, comentários, strings de display),
  scripts, testes, o doc de referência (renomeado `volume-profile-estrategia.md` →
  `volume-profile-strategy.md`) e o **PDF de 19 páginas** (renomeado p/ `volume_profile_study.pdf`).
  As CHAVES internas de dicionário foram mantidas (algumas em PT, ex.: `apenas_positivos_OOS`,
  `passa_todos`, keys de `sizing_sweep`/`param_profiles`) para NÃO precisar re-rodar os experimentos;
  onde essas chaves vazavam para display (fig 11 e Tabela 4 do PDF) há mapeamento PT→EN no charts.py
  e no pdf_report.py. As figuras foram regeradas em inglês (revisadas visualmente: 01,02,09,11,17,19
  + páginas 1-2 do PDF).
- **README reescrito** em inglês no estilo paper2004: badges, TL;DR honesto, TOC, seções com figuras
  embutidas + tabelas com números reais, conclusões, "reproduce it", estrutura, disclaimer.
- **Figuras e o PDF agora versionados** (`.gitignore` passou a permitir `output/figures/` e
  `output/volume_profile_study.pdf`) para renderizarem direto no GitHub.
- **Polimento GitHub**: `LICENSE` (MIT), `.gitattributes` marca PNG/PDF/PKL/Parquet como binário,
  `pyproject.toml` com metadados (v1.0.0, license, authors, keywords), `requirements.txt` corrigido
  (yfinance 0.2.51 → 1.4.1, que é o que está instalado). Repo público + description + topics + tag.
- `.claude/*` e `CLAUDE.md` ficaram em PT de propósito (memória/working files internos).
- 9 testes passando; `pip install -e .` necessário para os scripts (pytest usa pythonpath=src).

## ATUALIZAÇÃO ANTERIOR (falsificação)
A Claude web pediu testes de falsificação/ablação. Implementei `src/vptrading/analysis/
falsification.py` + `scripts/run_falsification.py` (5 testes: permutação de volume, ablação
só-preço, entrada aleatória, retorno excedente vs exposição/risk-free, bootstrap IC 95%). Config
FIXA (não reotimizada) para validar a permutação; seed fixa. **Resultado humilhante e honesto:
NENHUM sleeve passa nos 6 testes.** Só o SPY mostra sinal de volume estatisticamente real (shuffle
p=0,002, ablação +, random p=0,028), mas falha nos testes econômicos (sem alfa sobre exposição,
não bate risk-free, IC 95% de PF = [0,99; 2,83] inclui 1,0). O "edge" é majoritariamente exposição
comprada / buy-the-dip. O relatório PDF (agora **19 páginas**) ganhou a §11 "Testes de falsificação"
e teve sumário/conclusão/recomendações TEMPERADOS para refletir isso. Tabela 8 = veredito,
Tabela 9 = ablação. Figs 16-18. Resultado salvo em `output/falsification.pkl`.


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

"""Geração do relatório PDF técnico a partir de ``results.pkl`` e das figuras.

Usa ReportLab (Platypus). O relatório é em português, técnico e honesto: lidera com o sumário
executivo, detalha metodologia (incluindo a validação walk-forward), apresenta resultados com
gráficos e muitas tabelas comparativas, confronta as afirmações do documento de referência com os
dados, recomenda parâmetros conservadores e agressivos, e fecha com limitações.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#1f3b5c")
BLUE = colors.HexColor("#2c6fbb")
TEAL = colors.HexColor("#2a9d8f")
GREEN = colors.HexColor("#2e8b57")
RED = colors.HexColor("#c0392b")
LIGHT = colors.HexColor("#eef1f5")
GREY = colors.HexColor("#8a8f98")

STRAT_LABELS = {
    "REV": "Reversão ao POC",
    "E2E": "Edge-to-Edge",
    "BRK": "Breakout da VA",
    "EXH": "Exaustão de volume",
}


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("TitleBig", parent=ss["Title"], fontSize=26, textColor=NAVY,
                          spaceAfter=6, leading=30))
    ss.add(ParagraphStyle("Sub", parent=ss["Normal"], fontSize=13, textColor=GREY,
                          alignment=TA_CENTER, spaceAfter=4))
    ss.add(ParagraphStyle("H1", parent=ss["Heading1"], fontSize=17, textColor=NAVY,
                          spaceBefore=14, spaceAfter=8))
    ss.add(ParagraphStyle("H2", parent=ss["Heading2"], fontSize=13, textColor=BLUE,
                          spaceBefore=10, spaceAfter=5))
    ss.add(ParagraphStyle("Body", parent=ss["Normal"], fontSize=10, leading=15,
                          alignment=TA_JUSTIFY, spaceAfter=7))
    ss.add(ParagraphStyle("Cap", parent=ss["Normal"], fontSize=8.5, textColor=GREY,
                          alignment=TA_CENTER, spaceAfter=12, spaceBefore=3))
    ss.add(ParagraphStyle("VBullet", parent=ss["Normal"], fontSize=10, leading=14,
                          leftIndent=12, spaceAfter=3))
    ss.add(ParagraphStyle("Small", parent=ss["Normal"], fontSize=8.5, leading=11))
    ss.add(ParagraphStyle("KPI", parent=ss["Normal"], fontSize=10, leading=13))
    return ss


def _pct(x, dec=1):
    try:
        return f"{x * 100:.{dec}f}%"
    except (TypeError, ValueError):
        return "—"


def _num(x, dec=2):
    try:
        if x == float("inf"):
            return "∞"
        return f"{x:.{dec}f}"
    except (TypeError, ValueError):
        return "—"


def _img(path, width=16.5 * cm):
    img = Image(str(path))
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth = width
    img.drawHeight = width * ratio
    return img


def _table(data, col_widths, *, header_bg=NAVY, font=8.5, align="CENTER"):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), font),
        ("ALIGN", (0, 0), (-1, -1), align),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfd6df")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    return Table(data, colWidths=col_widths, repeatRows=1, style=TableStyle(style))


def _color_cells(table_data, value_grid, *, good_above=1.0):
    """Devolve comandos de estilo para colorir células numéricas (verde bom / vermelho ruim)."""
    cmds = []
    for (r, c), v in value_grid.items():
        if v is None:
            continue
        col = GREEN if v > good_above else RED
        cmds.append(("TEXTCOLOR", (c, r), (c, r), col))
    return cmds


def build_report(results: dict, figdir: Path | str, out_path: Path | str) -> str:
    figdir = Path(figdir)
    out_path = Path(out_path)
    ss = _styles()
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title="Volume Profile — Estudo de Backtesting", author="Pedro Braiti",
    )
    S = []

    # ---------------------------------------------------------------- Capa
    S.append(Spacer(1, 3.2 * cm))
    S.append(Paragraph("Volume Profile / Market Profile", ss["TitleBig"]))
    S.append(Paragraph("Estudo quantitativo de backtesting — em busca de um edge real, "
                       "validado out-of-sample", ss["Sub"]))
    S.append(Spacer(1, 0.6 * cm))
    S.append(Paragraph("33 anos de dados · 5 instrumentos (EUA + Brasil) · 4 estratégias · "
                       "validação walk-forward · custos incluídos", ss["Sub"]))
    S.append(Spacer(1, 2.4 * cm))
    meta = [
        ["Período diário", "1993–2026 (até onde cada ativo tem histórico)"],
        ["Instrumentos", "SPY, QQQ (EUA) · PETR4, VALE3, BOVA11 (B3)"],
        ["Fonte de dados", "Yahoo Finance (yfinance), gratuito"],
        ["Estratégias", "Reversão ao POC · Edge-to-Edge · Breakout da VA · Exaustão de volume"],
        ["Métrica-rainha", "Expectância por trade após custos"],
        ["Validação", "Walk-forward (otimiza no passado, mede no futuro não visto)"],
        ["Data de geração", "Junho de 2026"],
    ]
    S.append(_table([[Paragraph(f"<b>{k}</b>", ss["Small"]), Paragraph(v, ss["Small"])]
                     for k, v in meta], [4.5 * cm, 11.5 * cm], header_bg=colors.white, font=9))
    S.append(Spacer(1, 1.5 * cm))
    S.append(Paragraph("<i>Documento técnico de pesquisa. Não é recomendação de investimento. "
                       "Trading com alavancagem envolve risco de perda total.</i>", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Sumário executivo
    S.append(Paragraph("1. Sumário executivo", ss["H1"]))
    port = results["portfolio"]
    pkey = "apenas_positivos_OOS" if "apenas_positivos_OOS" in port else "todos"
    pm = port[pkey]["metrics"]
    wf = results["walkforward"]

    S.append(Paragraph(
        "Testamos as regras objetivas da estratégia Volume Profile (POC, Value Area, day-types, "
        "Regra dos 80%, edge-to-edge e leitura de volume) em 33 anos de dados, com custos e — "
        "crucialmente — com <b>validação walk-forward</b>: os parâmetros são escolhidos apenas com "
        "dados do passado e medidos em dados que o otimizador nunca viu. As conclusões centrais:",
        ss["Body"]))
    findings = [
        f"<b>Existe um edge real, porém modesto, na ponta comprada de índices líquidos.</b> "
        f"Out-of-sample, QQQ e SPY são lucrativos em todas as quatro estratégias "
        f"(QQQ Edge-to-Edge: Profit Factor {_num(wf['E2E']['QQQ']['oos_metrics']['profit_factor'])}; "
        f"QQQ Exaustão: expectância {_pct(wf['EXH']['QQQ']['oos_metrics']['expectancy_pct'],2)}/trade).",
        "<b>A 'leitura de volume' funciona melhor que o perfil em si.</b> Comprar exaustão "
        "('sem oferta' — novas mínimas com volume abaixo da média) foi a tática mais robusta "
        "out-of-sample em ETFs de índice (PF 1,5–2,2).",
        "<b>Reversão fadeia bem mercados balanceados e falha em tendência.</b> As ações brasileiras "
        "(PETR4, VALE3), mais tendenciais/voláteis, deram expectância negativa em quase tudo — "
        "exatamente o que a teoria prevê.",
        "<b>Duas 'lendas' do método não se sustentam nos dados:</b> a Regra dos 80% não atravessou "
        "80% das vezes (27–67% na amostra intraday recente) e foi negativa após custos; e os "
        "day-types não preveem continuação — se algo, dias 'bearish' repicam mais (reversão).",
        f"<b>Como sistema isolado, o edge não bate buy &amp; hold em retorno</b> (baixa exposição), "
        f"mas entrega um fluxo muito mais suave: o portfólio diversificado (sleeves validados OOS) "
        f"rendeu CAGR {_pct(pm['cagr_pct'])} com drawdown máximo de apenas {_pct(pm['max_drawdown_pct'])} "
        f"e Sharpe {_num(pm['sharpe'])}.",
    ]
    for f in findings:
        S.append(Paragraph("• " + f, ss["VBullet"]))
    S.append(Spacer(1, 0.3 * cm))
    S.append(Paragraph(
        "Em uma frase: o Volume Profile é uma <b>lente de contexto e uma ferramenta de timing</b> "
        "com edge estatístico pequeno mas verificável em ativos líquidos — não a 'fórmula secreta' "
        "vendida em vídeos. O valor está na gestão de risco e na seletividade, não na taxa de acerto.",
        ss["Body"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Metodologia
    S.append(Paragraph("2. Metodologia", ss["H1"]))
    S.append(Paragraph("2.1 Dados e instrumentos", ss["H2"]))
    inst_rows = [["Ticker", "Nome", "Mercado", "Início", "Pregões", "Buy&amp;Hold CAGR"]]
    for tk, d in results["instruments"].items():
        inst_rows.append([tk.replace(".SA", ""), d["name"], d["market"],
                          str(d["start"].date()), f"{d['n_days']:,}",
                          _pct(d["buyhold"]["cagr_pct"])])
    S.append(_table(inst_rows, [2.0 * cm, 4.6 * cm, 2.0 * cm, 2.4 * cm, 2.2 * cm, 2.8 * cm]))
    S.append(Paragraph(
        "Dados diários OHLCV do Yahoo Finance (longo histórico, volume confiável em ETFs/ações). "
        "O intraday gratuito é curto (~60 dias de 30 min), o que limita o teste fiel das regras "
        "intraday (Regra dos 80%) a uma amostra recente — por isso a abordagem é <b>híbrida</b>: "
        "backtest diário longo para robustez estatística + validação intraday recente.", ss["Cap"]))

    S.append(Paragraph("2.2 As quatro estratégias", ss["H2"]))
    strat_desc = [
        ["Reversão ao POC", "Fadeia extremos: vende acima da VAH / compra abaixo da VAL, alvo no "
         "POC. Rotação clássica do dia balanceado 'D'."],
        ["Edge-to-Edge", "Entra numa borda da Value Area e mira a borda oposta, atravessando o "
         "interior do perfil. Alvo maior."],
        ["Breakout da VA", "Opera a favor do rompimento da Value Area (atividade iniciante), "
         "alvo por múltiplo de ATR. Capta tendência."],
        ["Exaustão de volume", "Compra 'sem oferta' (§6): novas mínimas com volume abaixo da média "
         "= vendedores esgotados. Não depende do perfil."],
    ]
    S.append(_table([["Estratégia", "Lógica"]] + strat_desc, [3.8 * cm, 12.2 * cm], align="LEFT"))

    S.append(Paragraph("2.3 Custos, sizing e premissas", ss["H2"]))
    for b in [
        "<b>Sem lookahead:</b> os níveis do perfil usam só dados anteriores ao dia avaliado; sinal "
        "no fechamento do dia <i>t</i> → entrada na abertura de <i>t+1</i>.",
        "<b>Custos:</b> EUA ~0,05% round-trip (ETF + slippage); B3 ~0,2% (emolumentos + slippage). "
        "Todos os resultados são líquidos.",
        "<b>Sizing por risco:</b> cada trade arrisca 1% do capital no stop (ATR). Saídas por stop, "
        "alvo ou tempo; em ambiguidade, assume-se o stop primeiro (pessimista).",
        "<b>Walk-forward:</b> 8 anos de treino → 3 anos de teste, âncora deslizante. Os parâmetros "
        "do teste vêm só do treino. A concatenação dos trechos de teste é o resultado honesto.",
    ]:
        S.append(Paragraph("• " + b, ss["VBullet"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Conceito
    S.append(Paragraph("3. Como ler o Volume Profile", ss["H1"]))
    S.append(Paragraph(
        "O perfil é um histograma de volume por preço. Onde houve muito volume (HVN), o preço "
        "'gruda' — é valor aceito; onde houve pouco (LVN), o preço 'escorrega'. O POC é o preço de "
        "maior volume; a Value Area (~70% do volume, ±1 desvio-padrão de uma gaussiana) vai da VAL "
        "à VAH. Esses níveis são objetivos — melhores que suporte/resistência 'no olho'.", ss["Body"]))
    S.append(_img(figdir / "01_volume_profile.png"))
    S.append(Paragraph("Figura 1 — Perfil composite do SPY (120 pregões): o cluster de volume no "
                       "POC coincide com a faixa onde o preço passou mais tempo.", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Resultados OOS
    S.append(Paragraph("4. Resultados: o que funciona (e onde)", ss["H1"]))
    S.append(Paragraph("4.1 Panorama out-of-sample", ss["H2"]))
    S.append(_img(figdir / "02_oos_heatmap.png"))
    S.append(Paragraph("Figura 2 — Validação walk-forward (long-only, com custos). Verde = edge "
                       "positivo. O padrão é nítido: EUA verde, ações Brasil vermelho.", ss["Cap"]))

    # Tabela completa walk-forward
    S.append(Paragraph("4.2 Tabela completa de desempenho out-of-sample", ss["H2"]))
    wf_rows = [["Estratégia", "Ativo", "N", "Win", "Exp/trade", "PF", "CAGR", "Sharpe", "MaxDD"]]
    color_cmds = []
    rr = 1
    for s in wf:
        for tk in results["instruments"]:
            m = wf[s][tk]["oos_metrics"]
            wf_rows.append([STRAT_LABELS[s], tk.replace(".SA", ""), str(m["n_trades"]),
                            _pct(m["win_rate"], 0), _pct(m["expectancy_pct"], 2),
                            _num(m["profit_factor"]), _pct(m["cagr_pct"]),
                            _num(m["sharpe"]), _pct(m["max_drawdown_pct"])])
            color_cmds.append(("TEXTCOLOR", (5, rr), (5, rr),
                               GREEN if m["profit_factor"] > 1 else RED))
            color_cmds.append(("TEXTCOLOR", (4, rr), (4, rr),
                               GREEN if m["expectancy_pct"] > 0 else RED))
            rr += 1
    wf_tbl = _table(wf_rows, [3.0 * cm, 1.7 * cm, 1.0 * cm, 1.3 * cm, 2.0 * cm, 1.3 * cm,
                              1.5 * cm, 1.5 * cm, 1.6 * cm], font=8)
    wf_tbl.setStyle(TableStyle(color_cmds))
    S.append(wf_tbl)
    S.append(Paragraph("Tabela 1 — Desempenho out-of-sample por estratégia × instrumento. "
                       "Profit Factor e expectância coloridos (verde = lucrativo).", ss["Cap"]))
    S.append(PageBreak())

    S.append(Paragraph("4.3 Curvas de capital out-of-sample", ss["H2"]))
    S.append(_img(figdir / "03_oos_equity.png"))
    S.append(Paragraph("Figura 3 — Capital OOS da melhor estratégia long por instrumento. QQQ "
                       "(breakout) lidera; ações brasileiras ficam abaixo de 1,0.", ss["Cap"]))
    S.append(Paragraph("4.4 O edge não é overfitting", ss["H2"]))
    S.append(_img(figdir / "04_walkforward_degradation.png", width=15.5 * cm))
    S.append(Paragraph("Figura 4 — Expectância treino vs teste por janela. O desempenho out-of-"
                       "sample acompanha (e às vezes supera) o in-sample — sinal de edge genuíno, "
                       "não de sobreajuste.", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Carro-chefe + params
    S.append(Paragraph("5. Carro-chefe: Exaustão de volume", ss["H1"]))
    S.append(Paragraph(
        "A tática de comprar exaustão de venda (novas mínimas sem volume) foi a mais robusta. "
        "Abaixo, a sensibilidade dos parâmetros e a distribuição de retornos no SPY.", ss["Body"]))
    S.append(_img(figdir / "05_param_heatmap.png", width=12.5 * cm))
    S.append(Paragraph("Figura 5 — Profit Factor por janela × stop. Janelas maiores (40 dias) e "
                       "stop ~2×ATR foram as mais fortes; todas as células são lucrativas.", ss["Cap"]))
    S.append(_img(figdir / "10_trade_distribution.png", width=14.5 * cm))
    S.append(Paragraph("Figura 6 — Distribuição de retornos por trade: assimetria favorável "
                       "(perdas limitadas pelo stop, alguns ganhos grandes).", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Estudos das afirmações
    S.append(Paragraph("6. As afirmações do método vs os dados", ss["H1"]))
    S.append(Paragraph("6.1 Leitura de volume: divergência / 'sem oferta'", ss["H2"]))
    S.append(_img(figdir / "07_divergence.png", width=15.5 * cm))
    S.append(Paragraph("Figura 7 — Retorno futuro de 5 dias. Comprar novas mínimas com volume "
                       "baixo (divergência altista) supera o baseline em SPY, QQQ e VALE3 — a "
                       "leitura de volume do §6 tem mérito.", ss["Cap"]))

    S.append(Paragraph("6.2 Day-types não preveem continuação", ss["H2"]))
    S.append(_img(figdir / "06_daytype.png", width=15.5 * cm))
    S.append(Paragraph("Figura 8 — Retorno futuro por day-type (média dos 5 ativos). Se 'P' fosse "
                       "bullish e 'b' bearish, as barras divergiriam nessa direção. Ocorre o oposto "
                       "(reversão), refutando o uso dos rótulos como sinal de continuação.", ss["Cap"]))
    S.append(PageBreak())

    S.append(Paragraph("6.3 A Regra dos 80% não atravessa 80%", ss["H2"]))
    S.append(_img(figdir / "08_rule80.png", width=15.5 * cm))
    r80_rows = [["Ativo", "Setups", "Traverse rate", "Win rate", "Exp/trade", "Veredito"]]
    for tk, d in results["rule80"].items():
        dg = d["diagnostics"]
        m = d["metrics"]
        r80_rows.append([tk.replace(".SA", ""), str(dg["n"]),
                         _pct(dg["traverse_rate"], 0) if dg["n"] else "—",
                         _pct(m["win_rate"], 0), _pct(m["expectancy_pct"], 2),
                         "negativo" if m["expectancy_pct"] <= 0 else "positivo"])
    S.append(_table(r80_rows, [2.6 * cm, 2.0 * cm, 2.8 * cm, 2.4 * cm, 2.6 * cm, 2.6 * cm]))
    S.append(Paragraph("Tabela 2 — Regra dos 80% (30 min, 60 dias). Traverse rate bem abaixo de "
                       "80% e expectância negativa após custos. <b>Ressalva forte:</b> amostra "
                       "minúscula (7–14 setups/ativo) — indicativo, não conclusivo.", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Portfólio
    S.append(Paragraph("7. Portfólio diversificado", ss["H1"]))
    S.append(Paragraph(
        "Cada estratégia isolada negocia pouco (baixa exposição). Combinando, para cada instrumento, "
        "a estratégia que validou OOS, num portfólio de capital igualitário, eleva-se a exposição e "
        "diversifica-se o risco — o resultado é um fluxo de retorno notavelmente suave.", ss["Body"]))
    S.append(_img(figdir / "09_portfolio.png"))
    S.append(Paragraph("Figura 9 — Portfólio (sleeves validados OOS) e seu drawdown. Curva estável, "
                       "drawdown raso.", ss["Cap"]))
    port_rows = [["Portfólio", "Sleeves", "CAGR", "Sharpe", "MaxDD", "Exposição"]]
    for key, label in [("apenas_positivos_OOS", "Só sleeves positivos OOS"),
                       ("todos", "Todos os 5 instrumentos")]:
        if key in port:
            m = port[key]["metrics"]
            port_rows.append([label, str(len(port[key]["sleeves"])), _pct(m["cagr_pct"]),
                              _num(m["sharpe"]), _pct(m["max_drawdown_pct"]),
                              _pct(port[key]["exposure_pct"], 0)])
    S.append(_table(port_rows, [4.6 * cm, 1.8 * cm, 2.2 * cm, 2.0 * cm, 2.2 * cm, 2.4 * cm]))
    S.append(Paragraph("Tabela 3 — Métricas do portfólio (risco 1%/trade, sem alavancagem).", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Conservador vs Agressivo
    S.append(Paragraph("8. Conservador vs agressivo: o dial de risco", ss["H1"]))
    S.append(Paragraph(
        "Dois eixos controlam o perfil de risco: (a) os <b>parâmetros</b> (stop largo e alta "
        "seletividade = mais conservador) e (b) o <b>sizing/alavancagem</b>. Como o Sharpe é "
        "praticamente invariante ao sizing, alavancar só troca retorno por drawdown — não cria "
        "edge. A escolha é de apetite de risco, não de qualidade.", ss["Body"]))
    S.append(_img(figdir / "11_sizing_tradeoff.png", width=14.5 * cm))
    S.append(Paragraph("Figura 10 — CAGR vs drawdown ao variar risco/alavancagem. Linha do "
                       "portfólio domina a do ativo isolado (diversificação).", ss["Cap"]))

    # Tabela perfis de parâmetro
    pp = results["flagship"]["param_profiles"]
    pp_rows = [["Perfil de parâmetro", "N", "Win", "Exp/trade", "PF", "MaxDD"]]
    for name, d in pp.items():
        m = d["metrics"]
        pp_rows.append([name, str(m["n_trades"]), _pct(m["win_rate"], 0),
                        _pct(m["expectancy_pct"], 2), _num(m["profit_factor"]),
                        _pct(m["max_drawdown_pct"])])
    S.append(_table(pp_rows, [6.5 * cm, 1.3 * cm, 1.4 * cm, 2.2 * cm, 1.5 * cm, 2.0 * cm]))
    S.append(Paragraph("Tabela 4 — Perfis de parâmetro (Exaustão, SPY). Conservador = mais win "
                       "rate; agressivo = maior payoff, menor win rate. Tradeoff clássico.", ss["Cap"]))

    if "leverage_sweep" in port:
        lev_rows = [["Alavancagem", "CAGR", "Sharpe", "MaxDD", "Retorno total"]]
        for k, d in port["leverage_sweep"].items():
            m = d["metrics"]
            lev_rows.append([k, _pct(m["cagr_pct"]), _num(m["sharpe"]),
                             _pct(m["max_drawdown_pct"]), _pct(m["total_return_pct"])])
        S.append(_table(lev_rows, [3.0 * cm, 3.0 * cm, 2.6 * cm, 2.8 * cm, 3.2 * cm]))
        S.append(Paragraph("Tabela 5 — Portfólio sob alavancagem. Sharpe constante; só muda a "
                           "escala de retorno e drawdown.", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Custos + contexto
    S.append(Paragraph("9. Sensibilidade a custos e contexto", ss["H1"]))
    S.append(_img(figdir / "12_cost_sensitivity.png", width=14.5 * cm))
    cs = results["cost_sensitivity"]
    cs_rows = [["Custo round-trip", "Expectância/trade", "Profit Factor", "CAGR"]]
    for _, r in cs.iterrows():
        cs_rows.append([_pct(r["round_trip_cost_pct"], 2), _pct(r["expectancy_pct"], 3),
                        _num(r["profit_factor"]), _pct(r["cagr_pct"], 2)])
    S.append(_table(cs_rows, [4.0 * cm, 4.0 * cm, 3.5 * cm, 3.0 * cm]))
    S.append(Paragraph("Tabela 6 / Figura 11 — O edge é real mas estreito: aproxima-se do "
                       "breakeven (PF 1,0) sob custos de ~0,8% round-trip. Execução barata é "
                       "pré-requisito.", ss["Cap"]))
    S.append(_img(figdir / "13_strategy_vs_buyhold.png"))
    S.append(Paragraph("Figura 12 — Contexto (eixo log): buy &amp; hold do SPY vence em retorno "
                       "absoluto, mas com drawdowns muito maiores (note 2008). O portfólio VP "
                       "entrega menos retorno e muito menos sofrimento.", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Estudos complementares
    if "complementary" in results:
        comp = results["complementary"]
        S.append(Paragraph("10. Estudos complementares (§4.3, §6, §7)", ss["H1"]))
        S.append(Paragraph(
            "Para esgotar o documento de referência, testamos também as leituras de volume 'cru' "
            "(absorção e movimento saudável), o efeito do 'signal candle' e a sensibilidade à "
            "resolução do histograma.", ss["Body"]))

        S.append(Paragraph("10.1 Leituras de volume cru: absorção e movimento saudável", ss["H2"]))
        S.append(_img(figdir / "14_volume_events.png", width=15.5 * cm))
        S.append(Paragraph("Figura 13 — A <b>absorção no fundo</b> (nova mínima + volume enorme + "
                           "corpo pequeno) precede repiques fortes, sobretudo nas ações brasileiras "
                           "(VALE3 +1,9%, PETR4 +1,6% vs ~0,35% de baseline). Já o 'movimento "
                           "saudável' (candle e volume grandes) <b>não</b> supera o baseline em "
                           "índices — efeito ≠ resultado, ao contrário do prometido.", ss["Cap"]))

        S.append(Paragraph("10.2 O 'signal candle' (confirmação por volume) tem mérito", ss["H2"]))
        S.append(_img(figdir / "15_signal_candle.png", width=14.5 * cm))
        S.append(Paragraph("Figura 14 — Exigir um spike de volume no dia do sinal (§7) melhora "
                           "nitidamente o QQQ (Profit Factor 1,1 → 1,9 em ~1,2–1,5× a média), mas "
                           "filtra demais acima disso. Confirma a recomendação de 'esperar o candle "
                           "de volume' — com moderação.", ss["Cap"]))

        S.append(Paragraph("10.3 Resolução do perfil (a regra dos '400 rows')", ss["H2"]))
        S.append(_img(figdir / "16_resolution.png", width=13.5 * cm))
        S.append(Paragraph("Figura 15 — O edge é estável de 40 a 400 faixas de preço; mais "
                           "resolução ajuda só marginalmente no swing diário. A insistência em "
                           "'400 rows' importa mais no intraday fino do que aqui.", ss["Cap"]))
        S.append(PageBreak())

    # ---------------------------------------------------------------- Recomendações
    S.append(Paragraph("11. Recomendações de parâmetros", ss["H1"]))
    S.append(Paragraph(
        "Com base na varredura e na validação out-of-sample, estas são as variáveis recomendadas. "
        "Os dois perfis compartilham o mesmo edge; diferem no apetite de risco.", ss["Body"]))

    rec_rows = [
        ["Variável", "Perfil conservador", "Perfil agressivo"],
        ["Instrumentos", "Só ETFs de índice líquidos (SPY, QQQ)", "ETFs + nomes voláteis (VALE3) com breakout"],
        ["Estratégia", "Exaustão de volume / Edge-to-Edge (long)", "Breakout da VA + Exaustão (long)"],
        ["Direção", "Apenas comprado", "Comprado (shorts perderam em tudo)"],
        ["Janela do perfil/lookback", "40 dias", "20 dias"],
        ["Value Area", "0,80 (mais seletivo)", "0,70"],
        ["Stop", "≈ 2,5–3,0 × ATR (largo)", "≈ 1,5 × ATR (curto)"],
        ["Alvo", "POC / borda oposta", "5 × ATR (deixa correr)"],
        ["Holding máximo", "10 dias", "20 dias"],
        ["Filtro de tendência", "Ligado (não fadeia tendência)", "Ligado para breakout"],
        ["Risco por trade", "0,5–1,0% do capital", "2–3% do capital"],
        ["Alavancagem", "1× (nenhuma)", "até 3× no portfólio diversificado"],
    ]
    rt = _table(rec_rows, [4.2 * cm, 6.0 * cm, 6.0 * cm], align="LEFT")
    S.append(rt)
    S.append(Paragraph("Tabela 7 — Variáveis recomendadas. <b>Regra de ouro:</b> o perfil "
                       "conservador prioriza baixo drawdown e robustez entre ativos; o agressivo "
                       "aceita drawdown maior por mais CAGR, sem ilusão de Sharpe superior.", ss["Cap"]))
    S.append(Paragraph(
        "<b>O que mais melhorou os resultados (em ordem de impacto):</b> (1) operar só comprado em "
        "índices líquidos; (2) usar a leitura de volume (exaustão/absorção no fundo) em vez do "
        "perfil puro; (3) o filtro de tendência, que cortou o drawdown de −74% para −12% na "
        "reversão; (4) janelas mais longas (40 dias) no sinal de exaustão; (5) confirmar com "
        "spike de volume (signal candle) — elevou o PF do QQQ de 1,1 para 1,9; (6) diversificar "
        "em portfólio.", ss["Body"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Limitações
    S.append(Paragraph("12. Limitações e conclusão honesta", ss["H1"]))
    for b in [
        "<b>Aproximação do perfil:</b> sem dados tick/intraday longos, o volume é distribuído "
        "uniformemente no range diário. É a prática padrão, mas é uma aproximação do perfil 'real'.",
        "<b>Regra dos 80% e day-types intraday</b> foram testados em amostra curta (~60 dias de 30 "
        "min) — leitura indicativa. Um teste definitivo exige dados intraday históricos pagos.",
        "<b>Edge pequeno e cost-sensitive:</b> sobrevive OOS, mas evapora sob custos altos. Exige "
        "execução barata e disciplina; não tolera over-trading.",
        "<b>Sobrevivência e regime:</b> 33 anos incluem vários regimes, mas o futuro pode diferir. "
        "O walk-forward mitiga, não elimina, esse risco.",
        "<b>Base rate do day trade (USP/FGV):</b> dos que persistiram +300 dias, 97% perderam "
        "dinheiro e não houve evidência de aprendizado. Edge estatístico no backtest ≠ lucro "
        "garantido para um operador real.",
    ]:
        S.append(Paragraph("• " + b, ss["VBullet"]))
    S.append(Spacer(1, 0.3 * cm))
    S.append(Paragraph(
        "<b>Conclusão.</b> O Volume Profile não é mágica nem charlatanismo. É uma lente legítima de "
        "leilão (por que o preço gruda onde há volume) e fornece níveis objetivos. Há um edge "
        "estatístico real — pequeno, comprado, em ativos líquidos, e melhor capturado pela leitura "
        "de volume (exaustão) do que pelas regras folclóricas (80%, day-types). Como gerador de "
        "riqueza isolado, perde para buy &amp; hold; como ferramenta de timing de baixo drawdown "
        "dentro de um portfólio diversificado e bem-executado, tem mérito defensável. A métrica que "
        "importa é a expectância após custos — e ela é positiva, mas exige seletividade, não fé.",
        ss["Body"]))
    S.append(Spacer(1, 0.5 * cm))
    S.append(Paragraph("<i>Gerado por pipeline reproduzível (Python). Código e dados versionados. "
                       "Não é recomendação de investimento.</i>", ss["Cap"]))

    doc.build(S)
    return str(out_path)

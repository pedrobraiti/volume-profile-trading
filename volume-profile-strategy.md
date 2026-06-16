# Volume Profile / Market Profile — The strategy, the math, and the scenarios

> Reference document based on the strategy presented in the video, supplemented with
> research into the original sources (Steidlmayer, Dalton) and current technical material.
> Includes an honest critical section at the end: what is solid and what is folklore.

---

## 1. Where this comes from (and what the video doesn't tell you)

The video's strategy was **not invented by its creator**. It is a repackaging of **Market Profile**,
developed by **J. Peter Steidlmayer**, a floor trader at the *Chicago Board of Trade* (CBOT).
Steidlmayer formed the ideas in the 1960s–70s and presented the concept to the community as
"Market Profile" in **1984**, consolidating it in the book *Markets and Market Logic* (1986). **Jim Dalton**
expanded and popularized it all in *Mind Over Markets*.

Steidlmayer's original insight: by plotting **price on the vertical axis** and **time/activity on the
horizontal axis**, the chart forms a bell curve lying on its side — and he recognized in it the
**normal (Gaussian) distribution** he had studied in statistics in college. This is the
mathematical seed of everything that follows.

**An important distinction** the video blurs:

- **Market Profile (TPO)** — measures *time* spent at each price, using 30-minute blocks ("letters").
- **Volume Profile** — measures *volume* traded at each price. This is the version the video uses.

The concepts (POC, Value Area) are the same; only the metric changes (time vs. volume).

---

## 2. The theoretical foundation: Auction Market Theory (AMT)

The single premise: **every market is a continuous two-sided auction.**

- Price **rises** to attract sellers.
- Price **falls** to attract buyers.
- Where both sides agree, the trade happens and **volume accumulates**.

From this, two concepts the video summarizes well are derived:

| State | What happens | Result in the profile |
|---|---|---|
| **Equilibrium (balanced)** | Buyers and sellers agree. Market goes sideways. | Volume accumulates → **fair-value zone** (price "sticks") |
| **Imbalance (imbalanced)** | One side dominates. Price seeks a new level. | Price crosses quickly → **unfair value** (price "slips") |

> **Summary line from the video (correct):** "High volume = price sticks. Low volume = price slips."

Steidlmayer and Dalton also separate two behaviors:

- **Responsive activity** — the expected behavior. The market opens above value → sellers respond
  ("too expensive"); opens below → buyers respond ("too cheap"). It is the basis of
  mean reversion.
- **Initiating activity** — the unexpected behavior. Buying above value or selling below it. It is what
  starts trends.

---

## 3. The three central concepts

### 3.1 POC — Point of Control
The price level with the **highest volume** (the widest bar). It is the "center of gravity," the most
accepted price. Price tends to return to it. It can be based on volume (Volume POC) or on time
(TPO POC).

### 3.2 Value Area (VA)
The price range that contains **~70% of all activity**, bounded by:
- **VAH** (Value Area High) — top of the value area
- **VAL** (Value Area Low) — bottom of the value area

It is the market's "comfort zone": where buyers and sellers found the price fair.

### 3.3 HVN and LVN — Volume nodes
- **HVN (High Volume Node)** — wide bars. "Sticky" prices, acceptance, fair value.
  They act as support/resistance and are **packed with trapped positions**.
- **LVN (Low Volume Node)** — thin bars. The market's "fast lanes." Price crosses
  as if there were nothing there — because, structurally, there isn't.

---

## 4. The mathematical logic behind it

### 4.1 Why exactly 70%?

This is the point the video doesn't explain. The number comes from the **normal distribution**:

- In a Gaussian curve, **1 standard deviation** (±1σ) around the mean covers **68.2%** of the data.
- Steidlmayer **rounded 68.2% up to 70%** for convenience.

In other words: the Value Area is an attempt to capture "±1 standard deviation of price," assuming that
the day's distribution of trades approximates a bell curve. **Note:** this is the fragile assumption of
the entire method. Real market distributions have **fat tails** and skew; the "bell" is an
approximation, not a law.

### 4.2 The Value Area calculation algorithm (step by step)

It works the same for TPO or volume — just swap "TPOs" for "volume":

```
1. Sum the total volume of the profile.
2. Compute the target: 70% of that total  →  target = total × 0.70
3. Find the POC (the line with the highest volume). Start the VA with the POC only.
   Subtract the POC's volume from the target.
4. Look at the TWO lines above the POC and the TWO lines below.
   Sum each pair. Add to the VA the pair with the HIGHER combined volume.
5. Repeat step 4, always expanding in the direction of higher volume,
   until the accumulated volume reaches/exceeds 70% of the total.
6. The highest price included = VAH.  The lowest = VAL.
```

(When little is left and adding two prices would overshoot the target, prices are added one at a time.)

### 4.3 Why "number of rows = 400" in TradingView

The video tells you to switch from 24 to 400 rows. The logic is **resolution**: with 24 rows, each bar
aggregates a wide band of prices and the POC/VA becomes imprecise. With 400 rows, each bar covers a
thin band, and the nodes become sharp enough to serve as entry/stop levels. There's no magic —
it's just histogram granularity.

---

## 5. The "drawings" — the profile shapes (day types)

Here are the four scenarios the video draws. They come from the classic *day types* of
Market Profile.

### 5.1 "D" profile — Balanced market (Normal Day)
```
      ▓
    ▓▓▓▓▓
   ▓▓▓▓▓▓▓   ← POC in the center
    ▓▓▓▓▓
      ▓
```
- Heavy volume in the **middle**, thin at the extremes. Symmetric bell curve.
- Number of TPOs/volume **roughly equal** above and below the POC.
- **Meaning:** equilibrium, consolidation, no one in control.
- **Video's tactic:** *fade* the extremes. Sell at the top, buy at the bottom, target = POC in the middle.
  Pure rotation.

### 5.2 "P" profile — Bullish (short-covering / accumulation)
```
   ▓▓▓▓▓   ← POC and value at the TOP
   ▓▓▓▓▓
     ▓
     ▓     ← thin tail below
     ▓
```
- Heavy volume **at the top**, thin tail below.
- **Meaning:** rally in progress or strong rejection of low prices. Classically associated with
  **short-covering**. Value "rests" at the high → bullish bias.
- **Video's tactic:** wait for a pullback to the POC or to the "bounce" in the low tail, and buy.
- **Confirmation rule (video):** the day must **close above 50% of the range**. If it doesn't close there,
  it isn't a legitimate P — don't treat it as such.

### 5.3 "b" profile — Bearish (long-liquidation)
```
     ▓     ← thin tail on top
     ▓
     ▓
   ▓▓▓▓▓
   ▓▓▓▓▓   ← POC and value at the BOTTOM
```
- The exact mirror of the P. Heavy volume **at the bottom**, thin tail on top.
- **Meaning:** sellers in command. Classically, **liquidation of long positions**.
  Value rests at the bottom → bearish bias.
- **Video's tactic:** wait for a rally back to the POC or to the low-volume "bounce" on top, and sell.
- **Confirmation rule:** the day must **close below 50% of the range**.

### 5.4 Thin / trend profile (Trend Day)
```
   ▓
   ▓
   ▓
   ▓     ← thin, vertical column, no central zone
   ▓
   ▓
```
- No heavy central zone, no clear equilibrium. A thin column spread across a wide range.
  Range extension much greater than twice the *Initial Balance*; closes near the extreme.
- **Meaning:** an explosive move, usually *news-driven*. Price runs so fast that the
  large players don't have time to build a position.
- **Video's tactic:** **don't fight it**. Look for the small volume *clusters* within the
  thin profile — they are where aggressive position-adding occurred. In a bullish thin profile, these clusters
  become support on pullbacks.

> **Why this matters:** the Trend Day is the killer of the reversion strategy. Every *fade*
> tactic (D, P, b, 80% Rule) **fails** on a trend day. Knowing how to tell the shapes apart
> BEFORE trading is half the game.

---

## 6. Reading "raw" volume (the opening part of the video)

Before the profile, the video teaches three scenarios on the ordinary volume histogram:

| Scenario | Pattern | Interpretation |
|---|---|---|
| **1. Healthy move** | Large candle + high volume | Effort = result. A real move, tends to continue. |
| **2. Absorption** | Small candle + huge volume | "Invisible wall": a large player absorbs the orders. When the buyers are exhausted, the price falls. |
| **3. No supply** | Price rises + low volume | It isn't buying strength — it's the **absence of sellers**. Price drifts with no resistance. |

**Correct and important technical point from the video:** a **green** volume bar **does not mean buying** and
a red one does not mean selling. Every trade has a buyer *and* a seller — volume counts transactions,
not "who won." The bar's color simply follows the candle's color.

**Volume divergence** (a free alert system): price making new highs with volume bars getting
progressively **smaller** = a move running out of fuel (possible reversal). The inverse on a
decline = sellers exhausting themselves (possible bottom).

---

## 7. The video's trade setup (Signal Candle / Edge-to-Edge)

The "real" example in the video follows a model that circulates widely (also described by traders such
as Forrest Knight / TradeZella). The recipe:

1. **Context:** price reaches the edge of an HVN (after sweeping an LVN), at a key level
   (previous day's high/low, *overnight*, etc.).
2. **Trigger — "signal candle":** wait for a candle with **higher volume than the previous one** (doji,
   hammer, or shooting star) at the edge, **in the direction of the trade**, that **closes completely**.
   Never anticipate ("never front-run it").
3. **Entry:** at the close of that candle, with the volume spike confirming.
4. **Stop:** just below (or above) the node — if it breaks, the thesis is dead.
5. **Target:** the **opposite edge** of the profile (*edge-to-edge*), crossing the LVN.

The logic is that of the **trapped positions** in the HVNs: thousands entered at that price; when price
comes back, each one decides (doubles down, panic-sells, or breathes a sigh of relief). That reaction creates the reaction
at the level.

---

## 8. The "bonus tip" = the 80% Rule

The video ends with a rule presented as infallible. It is the **80% Rule** of
Market Profile, originating in the *Profile Reports* of **Dalton Capital Management (1987–1991)**.

**Correct statement:**
> If price **opens outside** the previous day's Value Area, then **re-enters** and is **"accepted"**
> (it stays inside for **two consecutive 30-minute periods** — 2 TPOs), there is a **~80%
> probability** of crossing the entire VA to the **opposite extreme**.

- **Bullish setup:** opens below the VAL → re-enters and is accepted → target = **VAH**.
- **Bearish setup:** opens above the VAH → re-enters and is accepted → target = **VAL**.

**A detail the video gets right:** **acceptance** is required (candles closing inside), not a wick
that merely touches and rejects.

**What the video distorts:** it says "it hits every time" and only later corrects to "the vast
majority." The number is **~80%, not 100%** — and even that 80% comes from observations in a private
newsletter from the 1980s, **not** from a peer-reviewed academic study. The rule works **in balanced
markets** and **fails on trend days** (again, the Trend Day).

---

## 9. Honest critical assessment

### What is solid
- **Auction Market Theory is a good description** of *why* price sticks where there is volume and
  slips where there isn't. As a contextual lens, it is legitimate and used by professionals.
- **POC, VAH, VAL, and volume nodes are observable, objective levels** — better than support/resistance
  lines drawn "by eye."
- The reading of **absorption / no supply / divergence** captures real order-flow dynamics.

### What is folklore (be careful)
- **The numbers 70% and 80% are not laws** — they are heuristics. The 70% is a rounding of 68.2%
  (1σ) that **assumes normality**, and markets are not perfectly Gaussian. The 80% comes from a
  commercial newsletter, not from independent research.
- **Volume Profile is not predictive.** Even the tool vendors themselves (OANDA, ForexTester)
  state explicitly that it **shows where volume has already occurred**, not where price is going;
  it needs price-action confirmation. There is no "secret formula."
- **Self-fulfilling component and arbitrage:** heavily watched levels can reinforce
  themselves — but they are also **anticipated** by those who place orders ahead of them, which erodes the edge.

### The point that matters more than anything
- **Win rate ≠ profit.** Reversion setups (D, P, b, 80% Rule) naturally have a
  **high win rate** with **asymmetric losses**: many small wins and, on a Trend Day,
  one big loss that wipes out several. What decides the outcome is **expectancy** after costs
  (spread, brokerage, slippage), not "it hits 80%."
- **Base rate (Brazilian data, USP/FGV, mini-index futures):** of those who persisted for +300 days, **97%
  lost money**; only ~1% beat the minimum wage; and there was **no evidence of learning**
  with experience over time.

### Red flags in the video (meta)
- The opening about "committing capital to push the price up and then letting it fall" describes
  **market manipulation** (something close to *spoofing* / *marking*) — which, despite the narration claiming
  it is "legal," is **illegal** in practice. It is a dramatic hook, not a lesson.
- The video is, at its core, a **marketing funnel** (discount code, "Flux Charts," a comment
  giveaway, links to other videos). The educational content is the bait.

---

## 10. Quick glossary

| Term | Meaning |
|---|---|
| **AMT** | Auction Market Theory — theory of the market as a continuous auction |
| **TPO** | Time Price Opportunity — 30-minute block used in Market Profile |
| **POC** | Point of Control — price with the highest volume/time |
| **VA / VAH / VAL** | Value Area and its high/low edges (~70% of activity) |
| **HVN / LVN** | High / Low Volume Node — high/low volume nodes |
| **IB** | Initial Balance — range of the first hour of the session |
| **Edge-to-edge** | Trading from one edge of the profile to the opposite, crossing the LVN |
| **80% Rule** | Open outside the VA + accepted re-entry → ~80% chance of crossing the entire VA |

---

## 11. Recommended next step

Before risking money, **backtest** the objective rules (80% Rule, fading extremes,
signal candle) with historical data for your instrument. Measure **expectancy**, not win rate:

```
Expectancy = (win rate × average gain) − (loss rate × average loss) − costs
```

If expectancy isn't positive after costs over hundreds of trades, the strategy
has no edge for you — regardless of how much it "makes sense" in the video.

---

### Main sources consulted
- Steidlmayer, *Markets and Market Logic* (1986); Dalton, *Mind Over Markets*.
- Value Area calculation documentation: Sierra Chart, CQG, TradingView, Trading Technologies.
- 80% Rule: MetroTrade, QuantVPS (originating in the Profile Reports of Dalton Capital, 1987–1991).
- Chague, De-Losso & Giovannetti, *Day Trading for a Living?* (USP/FGV, 2020).

> **Disclaimer:** an educational document. It is not investment advice. Leveraged trading
> involves the risk of total loss and, in the case of retail day trading, the evidence shows losses
> for the vast majority.

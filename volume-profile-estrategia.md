# Volume Profile / Market Profile — A estratégia, a matemática e os cenários

> Documento de referência baseado na estratégia apresentada no vídeo, complementado com
> pesquisa nas fontes originais (Steidlmayer, Dalton) e em material técnico atual.
> Inclui uma seção crítica honesta ao final: o que é sólido e o que é folclore.

---

## 1. De onde isso vem (e o que o vídeo não conta)

A estratégia do vídeo **não foi inventada pelo criador**. É uma repackaging do **Market Profile**,
desenvolvido por **J. Peter Steidlmayer**, trader do pregão do *Chicago Board of Trade* (CBOT).
Steidlmayer formou as ideias nos anos 1960–70 e apresentou o conceito à comunidade como
"Market Profile" em **1984**, consolidado no livro *Markets and Market Logic* (1986). **Jim Dalton**
expandiu e popularizou tudo em *Mind Over Markets*.

A sacada original de Steidlmayer: ao plotar **preço no eixo vertical** e **tempo/atividade no
horizontal**, o gráfico forma uma curva em sino deitada de lado — ele reconheceu ali a
**distribuição normal (gaussiana)** que tinha estudado em estatística na faculdade. Essa é a
semente matemática de tudo que vem depois.

**Distinção importante** que o vídeo embaralha:

- **Market Profile (TPO)** — mede *tempo* gastado em cada preço, usando blocos de 30 min ("letras").
- **Volume Profile** — mede *volume* negociado em cada preço. É a versão que o vídeo usa.

Os conceitos (POC, Value Area) são os mesmos; muda apenas a métrica (tempo vs. volume).

---

## 2. O fundamento teórico: Auction Market Theory (AMT)

A premissa única: **todo mercado é um leilão contínuo de duas pontas.**

- O preço **sobe** para atrair vendedores.
- O preço **cai** para atrair compradores.
- Onde os dois lados concordam, o negócio acontece e o **volume se acumula**.

Disso derivam dois conceitos que o vídeo resume bem:

| Estado | O que acontece | Resultado no perfil |
|---|---|---|
| **Equilíbrio (balanced)** | Compradores e vendedores concordam. Mercado lateraliza. | Volume se acumula → **zona de valor justo** (preço "gruda") |
| **Desequilíbrio (imbalanced)** | Um lado domina. Preço busca novo nível. | Preço atravessa rápido → **valor injusto** (preço "escorrega") |

> **Frase-resumo do vídeo (correta):** "Volume alto = preço gruda. Volume baixo = preço escorrega."

Steidlmayer e Dalton também separam dois comportamentos:

- **Atividade responsiva** — o esperado. Mercado abre acima do valor → vendedores respondem
  ("caro demais"); abre abaixo → compradores respondem ("barato demais"). É a base da
  reversão à média.
- **Atividade iniciante** — o inesperado. Compra acima do valor ou venda abaixo. É o que
  inicia tendências.

---

## 3. Os três conceitos centrais

### 3.1 POC — Point of Control
O nível de preço com **maior volume** (a barra mais larga). É o "centro de gravidade", o preço
mais aceito. O preço tende a retornar a ele. Pode ser baseado em volume (Volume POC) ou em tempo
(TPO POC).

### 3.2 Value Area (VA) — Área de Valor
A faixa de preço que contém **~70% de toda a atividade**, delimitada por:
- **VAH** (Value Area High) — topo da área de valor
- **VAL** (Value Area Low) — fundo da área de valor

É a "zona de conforto" do mercado: onde compradores e vendedores acharam o preço justo.

### 3.3 HVN e LVN — Nós de volume
- **HVN (High Volume Node)** — barras largas. Preços "pegajosos", aceitação, valor justo.
  Funcionam como suporte/resistência e estão **lotados de posições presas**.
- **LVN (Low Volume Node)** — barras finas. As "pistas rápidas" do mercado. O preço atravessa
  como se não houvesse nada ali — porque, estruturalmente, não há.

---

## 4. A lógica matemática por trás

### 4.1 Por que exatamente 70%?

Esse é o ponto que o vídeo não explica. O número vem da **distribuição normal**:

- Em uma curva gaussiana, **1 desvio-padrão** (±1σ) em torno da média cobre **68,2%** dos dados.
- Steidlmayer **arredondou 68,2% para 70%** por conveniência.

Ou seja: a Value Area é uma tentativa de capturar "±1 desvio-padrão de preço", assumindo que a
distribuição de negócios do dia se aproxima de um sino. **Atenção:** essa é a hipótese frágil de
todo o método. Distribuições reais de mercado têm **caudas gordas** e assimetria; o "sino" é uma
aproximação, não uma lei.

### 4.2 O algoritmo de cálculo da Value Area (passo a passo)

Funciona igual para TPO ou volume — troque "TPOs" por "volume":

```
1. Some o volume total do perfil.
2. Calcule o alvo: 70% desse total  →  alvo = total × 0,70
3. Encontre o POC (a linha de maior volume). Inicie a VA só com o POC.
   Subtraia o volume do POC do alvo.
4. Olhe as DUAS linhas acima do POC e as DUAS linhas abaixo.
   Some cada par. Adicione à VA o par com MAIOR volume combinado.
5. Repita o passo 4, sempre expandindo na direção do maior volume,
   até o volume acumulado atingir/ultrapassar 70% do total.
6. O preço mais alto incluído = VAH.  O mais baixo = VAL.
```

(Quando faltar pouco e adicionar dois preços ultrapassaria o alvo, adiciona-se um por vez.)

### 4.3 Por que "número de linhas (rows) = 400" no TradingView

O vídeo manda trocar de 24 para 400 linhas. A lógica é **resolução**: com 24 linhas, cada barra
agrega uma faixa larga de preços e o POC/VA fica impreciso. Com 400 linhas, cada barra cobre uma
faixa fina, e os nós ficam nítidos o bastante para servir de nível de entrada/stop. Não há mágica —
é só granularidade do histograma.

---

## 5. Os "desenhos" — os formatos de perfil (day types)

Aqui estão os quatro cenários que o vídeo desenha. Eles vêm dos *day types* clássicos do
Market Profile.

### 5.1 Perfil em "D" — Mercado balanceado (Normal Day)
```
      ▓
    ▓▓▓▓▓
   ▓▓▓▓▓▓▓   ← POC no centro
    ▓▓▓▓▓
      ▓
```
- Volume pesado no **meio**, fino nos extremos. Curva em sino simétrica.
- Nº de TPOs/volume **aproximadamente igual** acima e abaixo do POC.
- **Significado:** equilíbrio, consolidação, ninguém no controle.
- **Tática do vídeo:** *fade* nos extremos. Vende no topo, compra no fundo, alvo = POC no meio.
  Pura rotação.

### 5.2 Perfil em "P" — Bullish (short-covering / acumulação)
```
   ▓▓▓▓▓   ← POC e valor no TOPO
   ▓▓▓▓▓
     ▓
     ▓     ← cauda fina embaixo
     ▓
```
- Volume pesado **no topo**, cauda fina embaixo.
- **Significado:** alta em curso ou rejeição forte de preços baixos. Classicamente associado a
  **cobertura de shorts** (short-covering). Valor "descansa" no alto → viés de alta.
- **Tática do vídeo:** esperar pullback até o POC ou até o "ressalto" na cauda baixa, e comprar.
- **Regra de confirmação (vídeo):** o dia precisa **fechar acima de 50% do range**. Se não fechar,
  não é um P legítimo — não trate como tal.

### 5.3 Perfil em "b" — Bearish (long-liquidation)
```
     ▓     ← cauda fina em cima
     ▓
     ▓
   ▓▓▓▓▓
   ▓▓▓▓▓   ← POC e valor no FUNDO
```
- Espelho exato do P. Volume pesado **no fundo**, cauda fina em cima.
- **Significado:** vendedores no comando. Classicamente, **liquidação de posições compradas**.
  Valor descansa no fundo → viés de baixa.
- **Tática do vídeo:** esperar repique até o POC ou até o "ressalto" de baixo volume em cima, e vender.
- **Regra de confirmação:** o dia precisa **fechar abaixo de 50% do range**.

### 5.4 Perfil fino / de tendência (Trend Day)
```
   ▓
   ▓
   ▓
   ▓     ← coluna fina e vertical, sem zona central
   ▓
   ▓
```
- Sem zona central pesada, sem equilíbrio claro. Coluna fina espalhada por um range largo.
  Extensão de range muito maior que o dobro do *Initial Balance*; fecha perto do extremo.
- **Significado:** movimento explosivo, geralmente *news-driven*. O preço corre tão rápido que os
  grandes players não têm tempo de montar posição.
- **Tática do vídeo:** **não brigar contra**. Procurar os pequenos *clusters* de volume dentro do
  perfil fino — são onde houve adição agressiva de posição. Num perfil fino de alta, esses clusters
  viram suportes em pullbacks.

> **Por que isso importa:** o Trend Day é o assassino da estratégia de reversão. Toda tática de
> *fade* (D, P, b, Regra dos 80%) **falha** num dia de tendência. Saber distinguir o desenho
> ANTES de operar é metade do jogo.

---

## 6. Leitura de volume "cru" (a parte inicial do vídeo)

Antes do perfil, o vídeo ensina três cenários no histograma de volume comum:

| Cenário | Padrão | Interpretação |
|---|---|---|
| **1. Movimento saudável** | Candle grande + volume alto | Esforço = resultado. Movimento real, tende a continuar. |
| **2. Absorção** | Candle pequeno + volume enorme | "Parede invisível": um grande player absorve as ordens. Quando os compradores se esgotam, o preço cai. |
| **3. Sem oferta (no supply)** | Preço sobe + volume baixo | Não é força compradora — é **ausência de vendedores**. Preço flutua sem resistência. |

**Ponto técnico correto e importante do vídeo:** barra de volume **verde não significa compra** e
vermelha não significa venda. Todo negócio tem comprador *e* vendedor — o volume conta transações,
não "quem ganhou". A cor da barra só segue a cor do candle.

**Divergência de volume** (sistema de alerta gratuito): preço fazendo novas máximas com barras de
volume cada vez **menores** = movimento perdendo combustível (possível reversão). O inverso na
queda = vendedores se esgotando (possível fundo).

---

## 7. O setup de trade do vídeo (Signal Candle / Edge-to-Edge)

O exemplo "real" do vídeo segue um modelo que circula bastante (também descrito por traders como
Forrest Knight / TradeZella). A receita:

1. **Contexto:** preço chega à borda de um HVN (depois de varrer um LVN), num nível-chave
   (máx/mín do dia anterior, *overnight*, etc.).
2. **Gatilho — "signal candle":** esperar um candle de **volume maior que o anterior** (doji,
   martelo ou estrela cadente) na borda, **na direção do trade**, que **feche por completo**.
   Nunca antecipar ("never front-run it").
3. **Entrada:** no fechamento desse candle, com o spike de volume confirmando.
4. **Stop:** logo abaixo (ou acima) do nó — se romper, a tese morreu.
5. **Alvo:** a **borda oposta** do perfil (*edge-to-edge*), atravessando o LVN.

A lógica é a das **posições presas** nos HVNs: milhares entraram naquele preço; quando o preço
volta, cada um decide (dobra, vende no pânico, ou respira aliviado). Essa reação cria a reação
no nível.

---

## 8. A "dica bônus" = a Regra dos 80%

O vídeo termina com uma regra apresentada como infalível. Ela é a **Regra dos 80%** do
Market Profile, originada nos *Profile Reports* da **Dalton Capital Management (1987–1991)**.

**Enunciado correto:**
> Se o preço **abre fora** da Value Area do dia anterior, depois **reentra** e é **"aceito"**
> (permanece dentro por **dois períodos consecutivos de 30 min** — 2 TPOs), há **~80% de
> probabilidade** de atravessar toda a VA até o **extremo oposto**.

- **Setup de alta:** abre abaixo da VAL → reentra e é aceito → alvo = **VAH**.
- **Setup de baixa:** abre acima da VAH → reentra e é aceito → alvo = **VAL**.

**Detalhe que o vídeo acerta:** é preciso **aceitação** (candles fechando dentro), não um pavio
que só encosta e rejeita.

**O que o vídeo distorce:** ele diz "acerta toda vez" e só depois se corrige para "a grande
maioria". O número é **~80%, não 100%** — e mesmo esse 80% vem de observações de um boletim
privado dos anos 80, **não** de um estudo acadêmico revisado. A regra funciona **em mercados
balanceados** e **falha em dias de tendência** (de novo, o Trend Day).

---

## 9. Avaliação crítica honesta

### O que é sólido
- **Auction Market Theory é uma boa descrição** de *por que* o preço gruda onde há volume e
  escorrega onde não há. Como lente de contexto, é legítima e usada por profissionais.
- **POC, VAH, VAL e nós de volume são níveis observáveis e objetivos** — melhores que linhas de
  suporte/resistência desenhadas "no olho".
- A leitura de **absorção / sem oferta / divergência** capta dinâmicas reais de fluxo de ordens.

### O que é folclore (cuidado)
- **Os números 70% e 80% não são leis** — são heurísticas. O 70% é um arredondamento de 68,2%
  (1σ) que **assume normalidade**, e mercados não são perfeitamente gaussianos. O 80% vem de um
  boletim comercial, não de pesquisa independente.
- **Volume Profile não é preditivo.** Até fornecedores das ferramentas (OANDA, ForexTester)
  afirmam explicitamente que ele **mostra onde o volume já ocorreu**, não para onde o preço vai;
  precisa de confirmação de price action. Não existe "fórmula secreta".
- **Componente autorrealizável e arbitragem:** níveis muito observados podem se reforçar
  sozinhos — mas também são **antecipados** por quem coloca ordens na frente, o que corrói a vantagem.

### O ponto que importa mais que tudo
- **Taxa de acerto ≠ lucro.** Setups de reversão (D, P, b, Regra dos 80%) têm naturalmente
  **alta taxa de acerto** com **perdas assimétricas**: muitas vitórias pequenas e, num Trend Day,
  uma perda grande que apaga várias. O que decide é a **expectância** depois de custos
  (spread, corretagem, slippage), não o "acerta 80%".
- **Base rate (dado brasileiro, USP/FGV, mini-índice):** dos que persistiram +300 dias, **97%
  perderam dinheiro**; só ~1% superou o salário mínimo; e **não houve evidência de aprendizado**
  com o tempo de experiência.

### Bandeiras vermelhas no vídeo (meta)
- A abertura sobre "comprometer capital para empurrar o preço e depois deixar cair" descreve
  **manipulação de mercado** (algo próximo de *spoofing* / *marking*) — que, apesar da fala dizer
  ser "legal", é **ilegal** na prática. É um gancho dramático, não uma aula.
- O vídeo é, na essência, um **funil de marketing** (código de desconto, "Flux Charts", sorteio
  de comentário, links para outros vídeos). O conteúdo educativo é a isca.

---

## 10. Glossário rápido

| Termo | Significado |
|---|---|
| **AMT** | Auction Market Theory — teoria do mercado como leilão contínuo |
| **TPO** | Time Price Opportunity — bloco de 30 min usado no Market Profile |
| **POC** | Point of Control — preço de maior volume/tempo |
| **VA / VAH / VAL** | Value Area e suas bordas alta/baixa (~70% da atividade) |
| **HVN / LVN** | High / Low Volume Node — nós de alto/baixo volume |
| **IB** | Initial Balance — range da 1ª hora de pregão |
| **Edge-to-edge** | Operar de uma borda do perfil à oposta, atravessando o LVN |
| **Regra dos 80%** | Abertura fora da VA + reentrada aceita → ~80% de chance de cruzar a VA inteira |

---

## 11. Próximo passo recomendado

Antes de arriscar dinheiro, **backteste** as regras objetivas (Regra dos 80%, fade de extremos,
signal candle) com dados históricos do seu instrumento. Meça **expectância**, não taxa de acerto:

```
Expectância = (taxa de acerto × ganho médio) − (taxa de erro × perda média) − custos
```

Se a expectância não for positiva depois de custos ao longo de centenas de trades, a estratégia
não tem edge para você — independentemente de "fazer sentido" no vídeo.

---

### Fontes principais consultadas
- Steidlmayer, *Markets and Market Logic* (1986); Dalton, *Mind Over Markets*.
- Documentação de cálculo da Value Area: Sierra Chart, CQG, TradingView, Trading Technologies.
- Regra dos 80%: MetroTrade, QuantVPS (origem nos Profile Reports da Dalton Capital, 1987–1991).
- Chague, De-Losso & Giovannetti, *Day Trading for a Living?* (USP/FGV, 2020).

> **Aviso:** documento educativo. Não é recomendação de investimento. Trading com alavancagem
> envolve risco de perda total e, no caso de day trade de varejo, a evidência mostra prejuízo
> para a grande maioria.

# Has the Value Finder ever worked? A test on past seasons

> **Question.** The Value Finder flags players whose market value is low for their output, age
> and league. If that means anything, players it rated cheap should, later on, see their market
> value do better than players it rated expensive. Did they?
>
> Reproduce every number with `python scripts/backtest.py` (`src/scouting/metrics/backtest.py`,
> tested in `tests/test_metrics_backtest.py`). Data: transfermarkt-datasets (CC0), valuations to
> 11 June 2026.

## Answer in short

**Yes, but modestly.** Players the model rated cheap for their output saw their market value
hold up better over the next one to two years. Most of that raw advantage, though, comes from
*who* gets flagged (cheaper players lose less value), not from what the model adds. Once
players are compared with others of the same price, age, position and league, the model's own
contribution is small but consistent:

- a player valued at **half** what his output usually costs saw his market value do about
  **6-7% better** than a player priced exactly as expected;
- against like-for-like players, flagged players' median value change was **7-16% better**, but
  the share whose value actually rose was only **0-5 points higher**.

So the Value Finder is a reasonable place to **start** looking. It is not a prediction of who will
become valuable, and it does not replace watching players.

## How the test works

1. **Use only what was known then.** The value model is refitted on one season alone (2023/24, and
   then 2024/25), with the same rules the app uses: players with 900+ minutes and an up-to-date
   market value.
2. **Look forward.** Each player's market value at the end of that season (30 June) is compared
   with his latest value one or two years later.
3. **Compare fairly.** Raw comparisons flatter the model, because the players it flags are cheaper
   than average, and cheap players tend to lose less value in percentage terms. So three views are
   reported: the raw pattern, a like-for-like comparison and a regression with controls.

"Flagged" uses the Value Finder's default: valued at **50% or less** of the expected value.

## Results

### From 2023/24, two years later (to June 2026)

1,944 players were rated; 1,585 had a later valuation and could be followed.

| Rated cheap → expensive | Value vs expected (median) | Market value change (median) | Value rose |
| --- | --- | --- | --- |
| Cheapest fifth | 0.38x | ×0.80 | 36% |
| 2nd | 0.69x | ×0.71 | 30% |
| 3rd | 1.04x | ×0.62 | 29% |
| 4th | 1.54x | ×0.64 | 23% |
| Most expensive fifth | 2.85x | ×0.62 | 20% |

Most market values fell over the period (a typical player kept about two thirds of his value), so
what matters is the difference between groups. The cheapest fifth kept 80% of its value; the most
expensive fifth kept 62%.

| Group | Players | Market value change (median) | Value rose |
| --- | --- | --- | --- |
| Flagged (≤ 0.50x) | 281 | ×0.80 | 37% |
| Everyone else | 1,304 | ×0.67 | 26% |

- **Like-for-like** (same position group, age band and price band; 273 of 281 flagged players had
  a match): flagged players' median value change was **×1.12** that of their matches, and the
  share whose value rose was **3.9 points** higher.
- **Regression with controls** (current value, age, position, league strength): a player at half
  his expected value did **×1.07** better (coefficient -0.095 per unit of log value vs expected,
  robust standard error 0.029).

### The same test, one year later

| Base season and horizon | Flagged vs everyone else (median value change) | Like-for-like | Regression: half the expected value |
| --- | --- | --- | --- |
| 2023/24, 1 year | ×0.94 vs ×0.83 | ×1.16, +0.2 points rose | ×1.07 (SE 0.021) |
| 2023/24, 2 years | ×0.80 vs ×0.67 | ×1.12, +3.9 points rose | ×1.07 (SE 0.029) |
| 2024/25, 1 year | ×1.00 vs ×0.83 | ×1.07, +5.3 points rose | ×1.06 (SE 0.020) |

The direction is the same in all three tests, and the regression effect is three to five times
its standard error each time, so it is unlikely to be noise. Its size is small.

## What this does and does not show

- **Market value is the outcome, and it is a crowd estimate.** The test shows that the crowd later
  moved towards what the model saw. It does not show that the players got better, and it is not a
  transfer fee.
- **Selection.** Flagged players were a little less likely to have a later valuation in the
  2023/24 test (77% followed against 82%). If the missing ones were mostly careers that stalled,
  the result is slightly flattering.
- **Two base seasons only.** The data starts in 2023/24, so there is no longer history to test.
- **The model is simple on purpose.** It knows output, age and league, nothing about injuries,
  contracts, defending or passing. A small edge is what one should expect from it.

## What it means for using the app

Use the Value Finder to build a list worth watching, not a list worth buying. The flags beat a
coin toss, mainly by pointing to cheaper players, plus a small extra edge from the model itself.
The real work (video, live scouting, character, medical) is where most of the remaining
difference will be found.

---

**Resumo (PT):** testei o modelo de valor em épocas passadas. Ajustado só com dados de 2023/24 (e
depois de 2024/25), os jogadores que ele considerava baratos para a sua produção viram o valor de
mercado aguentar-se melhor nos 1-2 anos seguintes. Mas grande parte da vantagem vem de serem
jogadores mais baratos. Comparando com jogadores do mesmo preço, idade, posição e liga, o efeito do
modelo é pequeno mas consistente: cerca de 6-7% melhor para um jogador avaliado a metade do valor
esperado. Serve para escolher quem observar primeiro, não para prever quem vai valorizar.

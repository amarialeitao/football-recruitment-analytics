# Case study 2: a striker for under €1m

> **Question.** Casa Pia's most-used centre-forward in 2025/26, Cassiano, is 36 and was on a
> contract ending 30 June 2026. Which strikers aged 27 or under, valued at €1m or less, should
> the scouting department watch first?
>
> Data: transfermarkt-datasets (CC0), league games to 24 May 2026. Reproduce every number with
> `python scripts/case_study.py --player Cassiano --positions Centre-Forward --max-value 1000000 --max-age 27 --min-minutes 900 --rank-by performance`.

This is the second case study. The [first](case-study.md) replaced a right-back with the same
engine. Here the engine is pointed at a different problem, which needed one change to the method
(section 3).

## Answer in short

| Pick | Player | Club (league) | Age | Why | Main risk |
| --- | --- | --- | --- | --- | --- |
| Best output | **Barney Stewart** | Falkirk (Scotland) | 21.7 | 8 goals and 2 assists in 1,159 minutes: goals + assists per 90 in the top 9% of forwards | Only 39% of his team's minutes; contract status not in the data; value already up tenfold |
| Best value | **Sem van Duijn** | SC Telstar (Netherlands) | 21.8 | Top 22% for goals + assists per 90, in a stronger league, valued at about a ninth of what that output usually costs | Part-time too (33% of minutes, 1,013 minutes) |
| Most proven | **Zachary Sapsford** | Dundee United (Scotland) | 23.4 | The one regular among the top candidates: 2,278 minutes, 77% of his team's, 8 goals and 2 assists | Output is mid-table for a forward (percentile 46), not a clear upgrade |

The pattern behind all three is that **in this price range, strikers who score are part-timers,
and strikers who play every week score less**. The choice is between upside with a small sample
and reliability with modest output.

## 1. The need

- **Cassiano played 1,884 league minutes, 62% of the team's,** more than any other centre-forward
  in the squad. He is 36.5, valued at €150k, and his contract ended on 30 June 2026 in the data
  snapshot.
- **His output fell sharply this season.** Goals + assists per 90 dropped from percentile 71 in
  2024/25 to 26 in 2025/26 among 490 forwards with 900+ minutes in the eight leagues (6 goals and
  no assists, after 10 goals and 2 assists the season before).
- **The next centre-forward, Dailon Livramento, scored no goals** in 940 minutes (1 assist):
  percentile 3 for goals + assists per 90.

The club needs a striker who produces *more* than Cassiano did this season, not a copy of him.

## 2. The market

Of the 73 centre-forwards who played 1,800+ league minutes in 2025/26 across the eight leagues,
the median market value was **€4.5m**, and only 10 were valued at €1m or less. With a budget near
Casa Pia's record fee (€900k, see the [first case study](case-study.md)), a regular, productive
striker is rare. With 1,800+ minutes, aged 27 or under and €1m or less, there was **one**.

So the brief accepts **900+ minutes** (medium confidence) and treats the small sample as the main
risk, rather than pretending it is not there.

## 3. The brief, and one change to the method

| Criterion | Value | Why |
| --- | --- | --- |
| Position | Centre-forward | Like for like |
| Season | 2025/26 | Most recent full season |
| Leagues | 8 in scope | Markets Casa Pia can realistically buy in |
| Minutes | 900+ | Medium confidence; 1,800+ leaves one player (section 2) |
| Age | 27 or younger | Resale value, and time to develop |
| Market value | €1m or less | Close to the club's record fee |
| Market value age | Updated within a year | Outdated values make players look cheap |

**29 centre-forwards** meet the brief: 10 in Scotland, 9 in the Netherlands, 4 in Portugal, 2 in
Greece, 2 in Turkey, 1 in Denmark and 1 in Belgium.

**Ranking by output, not similarity.** The first case study ranked candidates by how closely they
matched the departing player's profile. That would be the wrong question here, because a close
match to Cassiano's 2025/26 season means low output. The engine now has an option to rank by
**performance score** (the average of a forward's profile percentiles) instead. Similarity to
Cassiano's role is still shown, for context.

## 4. The shortlist (top 10 by output)

| Player | Club | League | Age | Share of team min | G+A /90 | On-pitch +/- /90 | Perf. score | Value | Value vs expected | Contract | Similarity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Barney Stewart | Falkirk | Scotland | 21.7 | 39% | 0.78 | +0.47 | 74 | €1.0m | 0.22x | unknown | 20 |
| Sem van Duijn | SC Telstar | Netherlands | 21.8 | 33% | 0.62 | +0.53 | 67 | €800k | 0.11x | 2027 | 24 |
| Said Hamulic | Volos | Greece | 25.1 | 43% | 0.53 | +0.27 | 57 | €400k | 0.22x | 2027 | 37 |
| Pierre Landry Kaboré | Hearts | Scotland | 24.5 | 34% | 0.62 | +0.53 | 54 | €300k | 0.19x | 2028 | 30 |
| Zachary Sapsford | Dundee United | Scotland | 23.4 | 77% | 0.40 | -0.32 | 51 | €800k | 0.57x | 2028 | 58 |
| Güven Yalçın | Alanyaspor | Turkey | 27.0 | 33% | 0.72 | +0.36 | 49 | €1.0m | 0.45x | 2028 | 21 |
| Tyreece John-Jules | Kilmarnock | Scotland | 24.9 | 39% | 0.78 | -0.86 | 48 | €1.0m | 0.90x | 2026 | 29 |
| Matthew Hoppe | Sønderjyske | Denmark | 24.8 | 62% | 0.29 | +0.22 | 47 | €700k | 0.55x | 2028 | 55 |
| Richonell Margaret | Go Ahead Eagles | Netherlands | 25.3 | 34% | 0.35 | +0.26 | 45 | €600k | 0.30x | 2029 | 25 |
| Milan Zonneveld | SC Telstar | Netherlands | 22.2 | 35% | 0.67 | -1.00 | 44 | €450k | 0.19x | 2029 | 23 |

Only two of the 29 candidates play 60% or more of their team's minutes (Sapsford and Hoppe), and
the median is 39%. **No Liga Portugal striker makes the top ten**; the best, Diego Duarte (AVS),
ranks 18th.

## 5. The three alternatives

The picks follow the same fixed rules as the first case study, applied to the ten candidates
with the highest output.

**Best output: Barney Stewart (21, Falkirk, Scotland).** He started all 14 league games he played
and scored 8 goals with 2 assists in 1,159 minutes. That is 0.78 goals + assists per 90, in the
top 9% of forwards, and his goals alone are in the top 8%. The market noticed during the season:
his value went from €100k to €1.0m, which still leaves him at about a fifth of what that output
usually costs. The risks are a small sample (39% of minutes, medium confidence), a contract date
missing from the data (it has to be checked first) and no earlier season in scope to show it is
not a hot streak.

**Best value: Sem van Duijn (21, SC Telstar, Netherlands).** 5 goals and 2 assists in 1,013
minutes, 0.62 per 90, in the top 22% of forwards. He is valued at €800k, up from €325k, which is
about a ninth of what his output usually costs: the lowest ratio among the top candidates. The
Eredivisie is a stronger league than Scotland (index 66 against 32, Liga Portugal = 100), so his
numbers need less discounting. He played only 33% of his team's minutes, and his contract runs to
June 2027.

**Most proven: Zachary Sapsford (23, Dundee United, Scotland).** The rule for the third pick (the
youngest of the top ten who already plays at least 60% of his team's minutes) chooses him. In this
market it is better read as the *proven* option than the *young* one, because he is the only
regular near the top. In 2,278 minutes he scored 8 goals with 2 assists, 0.40 per 90. That is
clearly more than Cassiano this season (percentile 46 against 26), but in the middle of the
forward pool. He is also the candidate closest to Cassiano's role (similarity 58), valued at
€800k with a contract to 2028.

Also worth a look: **Said Hamulic (25, Volos, Greece)**, 0.53 per 90 and valued at €400k, and
**Pierre Landry Kaboré (24, Hearts, Scotland)**, 0.62 per 90 and valued at €300k. Both are
part-timers too.

## 6. Risks and what the data cannot show

- **Small samples.** Two of the three picks have about 1,000-1,200 minutes. A striker's per-90
  output over 12-14 starts can be a hot streak. This is the biggest risk, and it is why the
  confidence is medium, not high.
- **No shots or xG.** Public data for these leagues cannot separate good finishing (which tends to
  regress) from getting into good positions (which tends to last). That is the first question for
  video scouting.
- **League step.** Scotland's average squad value is about a third of Liga Portugal's (index 32),
  and European evidence is thin (6 Scottish games in 2025/26). The Netherlands (66) is a smaller
  step.
- **Why so few minutes?** The data cannot say whether the part-timers were injured, rotated,
  signed mid-season or behind a better player. Each case needs checking.
- **Market value is not a fee**, and contracts are a July 2026 snapshot (Stewart's is missing).

## 7. Next steps

1. Video scouting in this order: Stewart (highest output), van Duijn (best value, stronger league),
   Sapsford (the reliable option).
2. For Stewart and van Duijn, find out why they played about a third of the minutes; for Stewart,
   check the contract first.
3. Follow the part-timers' first months of 2026/27 before bidding: a second season at the same
   rate would turn medium confidence into high. The Player Profile's *change since last season*
   section will show it once the data is updated.

## Method

Same engine as the first case study (`src/scouting/case_study.py`, tested in
`tests/test_case_study.py`), with one option changed:

1. **Shortlist**: players meeting the brief, **ranked by performance score** (`rank_by =
   "performance"`), with similarity to the reference player kept for context.
2. **Best output**: the first candidate.
3. **Best value**: among the ten highest-output candidates with a performance score in the top
   quarter of the shortlist, the lowest value vs expected.
4. **Third pick**: among the ten highest-output candidates with at least the median performance
   score and at least 60% of their team's minutes, the youngest.

---

**Resumo (PT):** o avançado mais utilizado do Casa Pia em 2025/26, Cassiano, tem 36 anos, contrato
até 30/06/2026 e uma produção em queda (golos + assistências por 90 do percentil 71 para o 26).
Com um teto de €1m, ponta de lança que joga sempre e marca é raro: dos 73 com 1.800+ minutos, só
10 valem €1m ou menos. Os candidatos que produzem são quase todos suplentes ou titulares parciais
(mediana de 39% dos minutos). As três opções são Barney Stewart (maior produção), Sem van Duijn
(melhor relação produção/preço, numa liga mais forte) e Zachary Sapsford (a opção mais segura,
titular habitual). O maior risco é a amostra pequena: dois deles têm cerca de 1.000 minutos.

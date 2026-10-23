# Case study: replacing Casa Pia's right-back on a Casa Pia budget

> **Question.** Casa Pia's most-used player in 2025/26, right-back Gaizka Larrazabal, was on a
> contract ending 30 June 2026. Which three low-cost right-backs, in Liga Portugal or comparable
> leagues, should the scouting department watch first?
>
> Data: transfermarkt-datasets (CC0), league games to 24 May 2026. Reproduce every number with
> `python scripts/case_study.py`.
>
> See also the [second case study](case-study-2.md): a striker for under €1m.

## Answer in short

| Pick | Player | Club (league) | Age | Why | Main risk |
| --- | --- | --- | --- | --- | --- |
| Best value | **Triantafyllos Tsapras** | APO Levadiakos (Greece) | 24.2 | Strongest output in the shortlist (performance score 84), every minute of the season, valued at about a third of what that output usually costs | Valued at €1.5m, above any fee Casa Pia has paid since 2023 |
| Closest profile | **Luca Stephenson** | Dundee United (Scotland) | 22.3 | Most similar statistical profile to Larrazabal (similarity 64 of 100), attacking output in the top 3% of defenders | Contract to 2030: a fee is needed |
| Younger upside | **Filip Lissah** | Falkirk (Scotland) | 21.1 | Youngest regular among the most similar candidates, valued at €500k | Low attacking output so far; contract status not in the data |

All three come from leagues whose average squad value is about one third of Liga Portugal's.
The step up is the first thing video scouting has to test.

## 1. The need

Larrazabal was the player Casa Pia relied on most in 2025/26:

- **2,855 league minutes, 93% of everything the team played**, the highest share in the squad.
- **Goals + assists per 90 in the top 6%** of 711 defenders with 900+ minutes in the eight
  leagues in scope (0.28 per 90), and better each season: percentile 60 in 2023/24, 90 in 2024/25,
  94 in 2025/26.
- **Market value up from €1.0m to €4.0m in two seasons**, the highest among players the club
  owned (only a loanee was valued higher).
- **Contract ending 30 June 2026** in the data snapshot.

A key player on an expiring contract whose value has quadrupled is, for a club that sells to
grow, either a sale or a free departure. The data stops in July 2026, so it cannot say what
happened next; the case study prepares the replacement either way.

## 2. The budget

Since July 2023 the data records 54 arrivals at Casa Pia: **9 with a fee, 37 free** (free
transfers, loans, returns) and 8 with the fee unknown. **The highest fee paid was €900k.** Its
five largest sales, on the other hand, were between €3.0m and €6.5m.

The brief therefore caps **market value at €1.5m**: above the club's record fee, because a fee
is negotiated and market value is only an estimate, but well below Larrazabal's €4.0m.

## 3. The brief

| Criterion | Value | Why |
| --- | --- | --- |
| Position | Right-back | Like for like |
| Season | 2025/26 | Most recent full season |
| Leagues | 8 in scope (Portugal, Spain, Belgium, Netherlands, Greece, Turkey, Denmark, Scotland) | Markets Casa Pia can realistically buy in |
| Minutes | 1,800+ | High-confidence sample, not a few good games |
| Age | 29 or younger | Resale value and at least two good seasons ahead |
| Market value | €1.5m or less | Budget (section 2) |
| Market value age | Updated within a year | Outdated values make players look cheap |

**14 right-backs** meet the brief. They are ranked by similarity to Larrazabal's profile:
goals + assists, team goals for and against while on the pitch, share of team minutes, start
rate and yellow cards, each compared with all defenders.

## 4. The shortlist (top 10 by similarity)

| Player | Club | League | Age | Share of team min | G+A /90 | On-pitch +/- /90 | Perf. score | Value | Value vs expected | Contract | Similarity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Luca Stephenson | Dundee United | Scotland | 22.3 | 86% | 0.35 | -0.35 | 61 | €1.0m | 0.54x | 2030 | 64 |
| Lefteris Lyratzis | Panserraikos | Greece | 25.9 | 79% | 0.15 | -1.22 | 48 | €800k | 0.93x | 2027 | 47 |
| Marco Rente | FC Groningen | Netherlands | 28.8 | 74% | 0.28 | +0.24 | 75 | €1.3m | 0.39x | 2027 | 41 |
| Ilias Bronkhorst | Excelsior | Netherlands | 28.6 | 77% | 0.15 | -0.46 | 43 | €700k | 0.73x | 2028 | 40 |
| Triantafyllos Tsapras | APO Levadiakos | Greece | 24.2 | 100% | 0.39 | +0.54 | 84 | €1.5m | 0.35x | 2030 | 37 |
| Filip Lissah | Falkirk | Scotland | 21.1 | 72% | 0.08 | +0.00 | 53 | €500k | 0.37x | unknown | 34 |
| Danny Finlayson | Livingston | Scotland | 25.0 | 93% | 0.03 | -1.01 | 42 | €200k | 0.29x | 2028 | 33 |
| Pedro Pereira | Gençlerbirliği | Turkey | 27.9 | 86% | 0.07 | -0.31 | 49 | €1.2m | 0.81x | 2027 | 30 |
| Keelan Adams | Falkirk | Scotland | 24.1 | 63% | 0.05 | -0.19 | 47 | €250k | 0.27x | 2027 | 30 |
| Óscar Gil | OH Leuven | Belgium | 27.7 | 75% | 0.09 | -0.40 | 43 | €800k | 0.72x | 2026 | 28 |

*Performance score*: average of the player's defender-profile percentiles (0 to 100).
*Value vs expected*: market value divided by the value a model predicts from output, age and
league strength; below 1 means cheaper than similar players.

The only Liga Portugal right-back who meets the brief, Lucas Soares (Santa Clara), ranks 12th.

## 5. The three alternatives

Each pick answers a different question, chosen by a fixed rule from the ten most similar
candidates (see the method below), not by hand.

**Best value: Triantafyllos Tsapras (24, APO Levadiakos, Greece).** He played every league minute
of 2025/26 and has the highest performance score in the shortlist (84). His attacking output is
in the top 2% of defenders (0.39 goals + assists per 90), and his team scored more than it
conceded with him on the pitch (+0.54 per 90). He was already a regular in 2024/25 (77% of
minutes, attacking output in the top 9%). His value rose from €1.0m to €1.5m during the season
and sits at about a third of what this output usually costs. The catch is price: €1.5m is the
top of the budget, and his contract runs to 2030.

**Closest profile: Luca Stephenson (22, Dundee United, Scotland).** The most similar player to
Larrazabal in the shortlist (similarity 64; a typical pair of defenders scores about 30). He
gives the same kind of attacking output (0.35 goals + assists per 90, top 3%) and plays 86% of
his team's minutes. It is not a one-season spike: in 2024/25 he was in the top 17% with 81% of
minutes. Valued at €1.0m, but under contract to 2030, so a fee would have to be negotiated.

**Younger upside: Filip Lissah (21, Falkirk, Scotland).** The youngest of the most similar
candidates who already plays most of his team's minutes (72%). Valued at €500k, the cheapest of
the three. His attacking output is average for a defender (0.08 per 90), so he would be a
development signing rather than a like-for-like replacement. His contract date is missing in the
data, which can point to a loan: that has to be checked first.

Worth a look beyond the three: **Marco Rente (28, FC Groningen)**, the second-highest performance
score (75), valued at €1.3m with a contract to 2027. At 28 he offers less resale value.

## 6. Risks and what the data cannot show

- **League step.** Scotland and Greece have an average squad value of about one third of Liga
  Portugal's (index 32 and 33 against 100). Output at that level does not transfer one to one,
  and European results in the data are few (6 Scottish and 10 Greek games in 2025/26).
- **No defensive metrics.** Public data for these leagues has no tackles, interceptions, duels
  or positioning. For a full-back this is the biggest gap: this study can only say these players
  are available, trusted by their coaches and productive going forward.
- **Team effects.** On-pitch goal difference reflects the team as much as the player; Casa Pia's
  own figures are negative across the squad.
- **Market value is not a fee**, and contract dates are a snapshot from July 2026.
- **Regular season only.** Play-off rounds (Scotland, Greece) are not in the data, so minutes are
  slightly understated.

## 7. Next steps

1. Video scouting in this order: Tsapras (best output for the money), Stephenson (closest
   profile), Lissah (cheapest, development option).
2. Check contract and loan status for all three, and Lissah's in particular.
3. Use the app's Player Profile and Similar Players pages to widen the search: for example raise
   the age limit to bring in Marco Rente, or lower the minimum to 900 minutes for younger
   options.

## Method

`src/scouting/case_study.py` (tested in `tests/test_case_study.py`):

1. **Shortlist**: players meeting the brief, ranked by similarity to the reference profile
   (`find_similar`: z-scores within all defenders with 900+ minutes, Euclidean distance turned
   into a 0-100 score).
2. **Closest profile**: the most similar candidate.
3. **Best value**: among the ten most similar candidates with a performance score in the top
   quarter of the shortlist, the lowest value vs expected. The output floor avoids picking players
   who are cheap because they produce little.
4. **Younger upside**: among the ten most similar candidates with at least the median performance
   score and at least 60% of their team's minutes, the youngest.

---

**Resumo (PT):** o lateral-direito Gaizka Larrazabal foi o jogador mais utilizado do Casa Pia em
2025/26 (93% dos minutos), com contrato até 30/06/2026 e valor de mercado a subir de €1,0m para
€4,0m. Com um teto de €1,5m (a maior taxa paga pelo clube desde 2023 foi €900 mil), as três
alternativas são Triantafyllos Tsapras (melhor relação rendimento/preço), Luca Stephenson (perfil
mais parecido) e Filip Lissah (aposta jovem). O principal risco é o salto de nível: as três vêm
de ligas com cerca de um terço da força da Liga Portugal, e os dados públicos não têm métricas
defensivas.

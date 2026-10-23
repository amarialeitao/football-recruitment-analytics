# Methodology

This page explains how every number in the app is built, and why I chose to build it that way.
The guiding idea is that a scout or a sporting director should be able to ask "where does this
number come from?" about anything on screen and get a short, honest answer.

All thresholds live in `config/settings.yaml`, so changing a rule means changing one line, not
hunting through the code.

## 1. Data pipeline

```text
transfermarkt-datasets (CC0)
  └─ fetch_data.py     download once, verify SHA-256, check the schema, extract the scope to Parquet
      └─ build_dataset.py   stints → player x season x league table
          └─ app / case study   percentiles, league strength, value model, insights
```

- **Pinned version.** The download is checked against a SHA-256 hash. If the source publishes a
  new file, the pipeline stops instead of silently changing every number.
- **Schema check.** Required columns are checked before anything is extracted. The source mixes
  text and integer ids between tables, so ids are compared as text and then normalized.
- **Scope.** Eight leagues (Liga Portugal, LaLiga, Belgium, Netherlands, Greece, Turkey, Denmark,
  Scotland), seasons 2023/24 to 2025/26. Champions League games involving these clubs are kept for
  the league-strength evidence.
- **Nothing raw is committed.** `data/` is git-ignored; anyone can rebuild it with two commands.

The result is 11,553 player-season-league rows for 6,782 players, of whom 5,799 rows have 900+
minutes. The last game in the extract is from 24 May 2026.

## 2. The analysis table

One row per **player, season and league**. A player who moved between two clubs of the same
league in one season keeps one row; the club shown is the one where he played the most, and the
number of clubs is kept.

Position groups come from the source: Goalkeeper, Defender, Midfielder, Forward. The detailed
position (right-back, centre-back, …) is kept for filtering.

| Metric | Definition |
| --- | --- |
| Minutes, games, starts | Official league minutes and appearances |
| Share of team minutes | Minutes / (team league games x 90) |
| Start rate | Starts / games played |
| Goals, assists, goals + assists per 90 | Totals / minutes x 90 |
| Team goals scored / conceded per 90 (on pitch) | Goals the team scored or conceded while the player was on |
| On-pitch goal difference per 90 | The two above, subtracted |
| Yellow cards per 90 | Lower is better |
| Age | At 1 January of the season |
| Market value | Latest value on or before 1 July (start) and 30 June (end) of the season |

### On-pitch goals

The source has lineups, substitutions and goal events, but no "who was on the pitch" column, so I
rebuild it. For each player and game, a **stint** starts at 0 for starters or at the substitution
minute for substitutes, and lasts exactly the official minutes played. A goal counts for every
player whose stint contains its minute.

To make sure the events can be trusted, the goals in the events are compared with the final
score of each game. They match in 6,255 of 6,260 games. The five that do not are kept, but their
on-pitch goals are left empty rather than guessed.

On-pitch goal difference describes the team as much as the player. It is useful to see who plays
in the good and the bad moments, not to rank individual defending.

## 3. Percentiles

A raw "0.28 goals + assists per 90" means little on its own. Each metric is turned into a
percentile against **players of the same position group, in the same season, across all eight
leagues, with at least 900 minutes**.

- Percentiles go from 0 to 100, and "lower is better" metrics (goals conceded, yellow cards) are
  flipped so **100 is always best**.
- Players below 900 minutes keep their row but get no percentile: a few good games should not
  produce a "top 5%".
- Each percentile carries the size of its comparison group (for example, 711 defenders in
  2025/26), so the app can say who the player is compared with.

Comparing across leagues on purpose answers the recruitment question ("how does he compare with
everyone we could buy?"). League strength is shown next to it rather than mixed into it, so the
reader can see both and decide.

## 4. Confidence

Every insight carries a confidence badge, decided by the weakest of two samples:

| | Low | Medium | High |
| --- | --- | --- | --- |
| Player's minutes | under 900 | 900+ | 1,800+ |
| Players in the comparison group | under 30 | 30+ | 100+ |

The wording follows the confidence: an observation ("top 11% for start rate") is always shown,
while an interpretation becomes more cautious when the sample is small.

## 5. League strength

A top-10% player in Scotland and a top-10% player in Spain are not the same thing, so every page
shows how strong the player's league is.

- **Index:** the average club squad value of each league (sum of its players' end-of-season
  values), relative to Liga Portugal = 100.
- **Supporting evidence:** points and goal difference per game of each league's clubs against
  other leagues in European games, with the number of games behind it.

I first wanted to use Club Elo, but it blocks scripted access, so the index uses the same open
dataset as everything else. Its limit: the European games in the source are the Champions League
and its qualifiers only, which is thin evidence for leagues whose clubs rarely go far.

## 6. Performance score and value model

**Performance score** is the average of the player's profile percentiles for his position group
(0 to 100). The profile per group is defined once in `src/scouting/metrics/catalog.py`.

**Expected market value** comes from a linear regression, fitted separately for each position
group, of `log10(market value)` on performance score, age, age squared and league strength
(log10 of the index). Only players with 900+ minutes and an up-to-date value are used.

| Position group | R² |
| --- | --- |
| Goalkeeper | 0.75 |
| Forward | 0.70 |
| Midfielder | 0.66 |
| Defender | 0.65 |

**Value vs expected** is actual value divided by expected value. Below 1, the market values the
player less than others with similar output, age and league. The app reads 0.7 or below as "valued
below his output" and 1.5 or above as "valued above it".

I kept the model deliberately simple. It is easy to explain, it is fitted on the same population
it is used on, and its weak spots are clear: market values are crowd estimates, and anything the
data does not measure (defending, passing, injuries, character) ends up in the error.

**Outdated values.** If a player's value had not been updated for more than a year at the end of
the season, it is marked as stale and left out of the model and the Value Finder, because an old
value makes a player look cheap.

## 7. Similar players

Used when the question is "we are losing this player, who does a similar job?".

1. Candidates: same position group, 900+ minutes.
2. Each profile metric is standardized (z-score) within that pool, with "lower is better" metrics
   flipped. Weights can change how much each metric counts.
3. Similarity = `100 x exp(-d / sqrt(k))`, where `d` is the distance between the two players in
   standardized units and `k` the number of metrics.

An identical profile scores 100; a typical pair of players scores around 30. My first version
used cosine similarity, but almost every player scored 98 to 100, because it ignores intensity: a
player with half the output in every metric looked identical. Distance fixed that.

Filters (age, value cap, leagues) only change which candidates are shown, not the pool used for
standardization, so scores stay comparable as filters change.

The score says who plays a similar **statistical role** with the data available, not who is
equally good.

## 8. Potential

These are **signals, not predictions**. For players aged 23 or younger:

- **Minutes for age:** share of team minutes compared with regulars (900+ minutes) of the same
  position group and age (in whole years) in the same season.
- **Starts for age:** the same comparison for start rate.
- **Value growth:** change in market value over the season.

A signal is strong at percentile 75+ (or 25%+ value growth). Groups with fewer than five peers get
no percentile.

The comparison with regulars matters. When young players were compared with everyone their age,
63% of them met two or more signals just by playing, which made the page useless. Against regulars
of the same age, 30% do.

## 9. Automatic insights

The short texts on each page follow four rules:

1. **Confidence comes from the sample** (section 4), and the weakest sample wins.
2. **Observation and interpretation are separate.** "Top 6% of defenders for goals + assists" is
   an observation; "valued below his output" is an interpretation and is worded more carefully when
   confidence is lower.
3. **Evidence travels with the text.** Each insight has an "observed data" view with the numbers
   behind it.
4. **No input, no insight.** If a number is missing, the insight is not written.

A metric at percentile 75+ is a strength, at 25 or below a weakness. Every text exists in English
and Portuguese.

## 10. Data quality

The Data Quality page and the status board answer "can I trust what I am looking at today?". Each
area is OK or ATTENTION, with a one-line reason, and the thresholds come from the configuration:

| Area | Rule |
| --- | --- |
| Data freshness | Last game no more than 120 days ago |
| Profile completeness | Key fields (age, position, foot, height, market value) at least 90% complete |
| Match events | At most 1% of games where events do not match the score, and no duplicate rows |
| Market values | At most 5% of regulars with a value older than a year |
| Comparison groups | The smallest peer group behind any percentile has at least 100 players |

A missing contract date is reported separately and not counted as missing data: it is expected
for loans and free agents.

## 11. Limitations

- **No defensive, passing, shooting or xG metrics** in the public data for these leagues. The app
  lists them as "not available" on every profile.
- **On-pitch metrics reflect the team.**
- **League strength is a proxy** with thin European evidence.
- **Three seasons only**, regular season only.
- **Market values are estimates, not fees;** contract dates are a July 2026 snapshot.
- **Rule-based thresholds** (900 minutes, percentile 75, and so on) are reasonable defaults, not
  tuned values. They are all in the configuration, so they can be challenged and changed.

The tool helps decide who to watch first. It does not replace watching them.

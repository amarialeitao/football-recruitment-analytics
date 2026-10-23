# Football Recruitment Analytics

Recruitment support tool for a club with a limited budget in **Liga Portugal**: find, profile and compare
players using open data, with every insight showing how much evidence (minutes played) supports it.

> Work in progress. This README will be expanded as the project is built.

## Scope (MVP)

- **Leagues:** Liga Portugal plus seven comparable leagues (LaLiga, Belgium, Netherlands, Greece, Turkey,
  Denmark, Scotland).
- **Seasons:** 2023/24 to 2025/26.
- **Data:** [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) (CC0 1.0).
  Raw data is downloaded locally by a script and never committed to this repository.

## Quick start

```bash
pip install -e ".[dev]"
python scripts/fetch_data.py      # download the source (cached) and extract the scope
python scripts/build_dataset.py   # build the player x season x league table
streamlit run app.py
```

Run the tests with `pytest`. On Windows, use `py` instead of `python`.

## AI Scouting Notes (optional, disabled)

The Player Profile page can show a short written profile drafted by an LLM. The feature is
**implemented and tested but switched off in this repository**: with the default configuration
nothing about it appears in the app, and no request is ever sent to a model.

**What the model receives.** Only a JSON of facts built from the selected player's row
(`src/scouting/llm_notes.py`, `build_facts`): name, club, league, season, position, age,
minutes, games and starts, the position group's metrics with their percentiles, the size of the
comparison group, the confidence level, market value and expected value, the league strength
index, the contract date, the automatic insights and the list of metrics public data does not
cover. No web access and no free text from users.

**Safeguards.**

- The instructions forbid any number, event or opinion that is not in the facts, and require
  the text to state the confidence level and the main data gaps.
- Every number in the answer is checked against the facts (`check_numbers`); numbers that
  cannot be traced are shown as a warning under the note.
- The note is labelled as AI-generated, with the model name.
- API errors never break the page; each note is cached per player and language while the app runs.

**How to enable it**

1. Install the optional dependency:

   ```bash
   pip install -e ".[llm]"
   ```

2. Set the API key as an environment variable (never in a file that is committed; `.env` is
   git-ignored):

   ```powershell
   # Windows PowerShell (current session)
   $env:ANTHROPIC_API_KEY = "your-key"
   ```

   ```bash
   # macOS / Linux
   export ANTHROPIC_API_KEY="your-key"
   ```

3. Turn the feature on in `config/settings.yaml`:

   ```yaml
   llm:
     enabled: true
     provider: anthropic
     model: claude-haiku-5-5       # any model name your key can use
     api_key_env: ANTHROPIC_API_KEY
     max_tokens: 600
   ```

4. Restart the app. The Player Profile page now shows an **AI Scouting Note** card with a
   *Generate note* button. Each click sends one request to the provider, which is billed to the
   key's account.

To switch it off again, set `enabled: false` or unset the environment variable. If one of the
three conditions is missing, the feature stays hidden.

## License

Code released under the MIT License. Data remains subject to its source's license and terms.

---

**Resumo (PT):** ferramenta de apoio ao recrutamento para a Liga Portugal, construída com dados abertos.
Interface em inglês com opção de português. As notas de scouting por IA estão implementadas mas
desligadas; a secção *AI Scouting Notes* explica como ativá-las (dependência opcional, variável de
ambiente com a chave e `llm.enabled: true` em `config/settings.yaml`).

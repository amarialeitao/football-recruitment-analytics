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
pytest
```

## License

Code released under the MIT License. Data remains subject to its source's license and terms.

---

**Resumo (PT):** ferramenta de apoio ao recrutamento para a Liga Portugal, construída com dados abertos.
Interface em inglês com opção de português.

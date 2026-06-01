# race-data-validator

Local validation tool for race-results CSVs.
Pairs with the **Race Results Data Contract** (current: v2.2.1).

## What it does

Drag your CSV into a local web app. The app runs every rule in the contract
against your file and tells you exactly what's wrong, with row numbers and
fix hints. Nothing leaves your machine.

## Install (one-time)

You need Python 3.11+ and `pip`. Then:

```bash
pip install --upgrade git+https://github.com/begumcum/race-data-validator@v0.1.0
```

To verify the install worked:

```bash
race-validator --version
```

## Run

```bash
race-validator
```

A browser tab opens at `http://localhost:8501`. Drop your CSV, click validate.
Press `Ctrl-C` in the terminal when you're done.

## Updating

When a new version ships, re-run the install command with the new tag:

```bash
pip install --upgrade git+https://github.com/begumcum/race-data-validator@v0.1.1
```

## What's checked in v0.1.0

- **File-level rules** (§1): filename format, UTF-8 encoding, Unix line endings, no BOM
- **Reference data lookups** (§4, read-only): `country_id`, `region_id`, `series_id`,
  `circuit_id`, `(sport, discipline, category)` triple, `nationality_code`
- **Normalization integrity** (§3a): every `_normalized` value matches the
  canonical normalizer output applied to its companion `_raw` field

Reference data (countries, regions, categories, series, circuits) is bundled
inside the library. Updates to that data ship as new library versions.

## What's NOT checked in v0.1.0 (deferred to v0.2.0)

- Driver / team / car_model lookups against BigQuery dim tables
- Interactive entity resolution (fuzzy matching, "add new" prompts)

For now, format checks still apply to driver/team/car_model fields — the
lookup against the dynamic dim tables is the v0.2.0 work.

## License

Proprietary. Internal use only.

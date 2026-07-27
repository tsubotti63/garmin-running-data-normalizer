# Contributing

Thank you for helping improve Garmin Running Data Normalizer.

## Scope

Contributions may improve Garmin-focused normalization, deterministic QA,
documentation, synthetic fixtures, tests, and public-safe operational tooling.
Hosted processing, medical/coaching interpretation, non-Garmin platform
generalization, and personal-data examples are outside the project boundary.

Open an Issue before a change that affects CLI behavior, stable output paths,
schemas, lifecycle semantics, privacy, or another public contract. A proposal
does not itself authorize a breaking change.

## Development setup

Use Python 3.11 or later:

### macOS / Linux

```bash
git clone https://github.com/tsubotti63/garmin-running-data-normalizer.git
cd garmin-running-data-normalizer
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test,release]'
```

### Windows PowerShell

```powershell
git clone https://github.com/tsubotti63/garmin-running-data-normalizer.git
Set-Location garmin-running-data-normalizer
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test,release]"
```

`python` must resolve to Python 3.11 or later. When selecting among multiple
installed versions through the Windows Python launcher, contributors may use
`py -3.11 -m venv .venv` instead.

Create a focused branch, keep the change to one reviewable theme, and open a
Pull Request against `main`.

## Validation

Run the relevant tests and the full public gate before requesting merge:

```bash
python -m unittest discover -s tests -v
python -m pytest
python scripts/validate_bootstrap.py
python scripts/static_policy_scan.py
python scripts/validate_platform_alignment.py
python scripts/validate_schema_contract.py
python scripts/validate_public_command_examples.py
python scripts/validate_public_history.py --ci
python -m build
python -m twine check --strict dist/*
```

Document which commands passed. Add or update synthetic tests when behavior
changes. Documentation examples must use placeholders or visibly synthetic
data and must match the tested CLI.

## Privacy and public evidence

Never commit or attach:

- a real Garmin Export or full personal Run-All output;
- real Activity rows, IDs, stable keys, memo text, or coordinates;
- private filenames, paths, hashes, exact dates, or locations;
- credentials, cookies, tokens, or private review evidence.

Use the tracked synthetic fixtures for reproduction. Follow
[SUPPORT.md](SUPPORT.md) for a public-safe bug report.

## Stable contracts and approval boundaries

Preserve the documented `1.x` compatibility boundary unless an explicitly
reviewed change says otherwise. Missing data is not zero, unresolved
relationships are not guessed, and absence from a later Snapshot is not a
deletion instruction.

A contribution, review, or merged Pull Request does not authorize a release,
tag, PyPI upload, publication, privacy-boundary change, or other
Human-controlled action.

## Pull Request checklist

- Explain the problem, scope, and any changed public contract.
- Link the relevant Issue for behavior or contract changes.
- Include tests and validators run.
- Confirm examples and fixtures are synthetic.
- Confirm no personal Garmin data or private evidence is included.
- Update the smallest authoritative documentation set.
- Identify any Human approval still required.

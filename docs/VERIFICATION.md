# Verification for the workspace update

- 20 unit/API tests pass without a live database, model downloads, or provider calls.
- Desktop and mobile browser smoke checks pass in the existing local Chrome installation.
- Browser checks cover sample queries, schema switching, filtering and empty states, keyboard tabs, CSV export, simulated live responses, HTML escaping, spreadsheet formula escaping, and API error recovery.
- The README screenshot was captured from the actual workspace in sample mode.
- Python source compilation and JavaScript syntax checks pass.

The live PostgreSQL → Chroma → LLM integration and a full Docker build have not been run for this update. Browser API responses are simulated for UI testing. Historical evaluation reports predate these changes and should not be interpreted as new benchmark results.

Reproduce the unit tests with `python -m pytest tests/unit -q` from `backend/` after installing `requirements-test.txt`. For optional browser checks, install the `playwright` Python package and run `python backend/scripts/check_ui.py --browser <path-to-existing-chrome-or-edge>` from the repository root. No browser download is performed by that script.

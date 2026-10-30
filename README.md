# TaskBoard QA Automation

![tests](https://github.com/sohaebgamal/taskboard-qa-automation/actions/workflows/tests.yml/badge.svg)

An automated test suite that combines functional QA and security testing, written with Pytest and Playwright and run by GitHub Actions on every push.

The system under test is **TaskBoard**, a small Flask app in this repository, built only to be tested. It runs on your own machine, so the suite never touches an external site. Do not deploy it.

## What is covered

| Layer | Tests | Examples |
|---|---|---|
| API (`tests/api`) | 33 | Task CRUD, validation, boundary values, data persistence |
| Security (`tests/security`) | 26 | IDOR, role checks, login lockout, user enumeration, SQL injection, cookie flags, security headers |
| UI (`tests/ui`) | 13 | Login, task flows after reload, stored XSS, user isolation, admin visibility |

**Total: 72 tests.**

## Do the tests catch real bugs?

A green suite only matters if it turns red when the app breaks. `scripts/fault_check.py` switches on one known bug at a time, re-runs the suite and fails if any bug goes unnoticed.

| Injected bug | Failing tests |
|---|---|
| `idor`: users can reach each other's tasks | 3 |
| `admin_open`: admin endpoint has no role check | 1 |
| `no_lockout`: unlimited login attempts | 1 |
| `user_enum`: login reveals which usernames exist | 4 |
| `xss`: task titles rendered as HTML | 1 |
| `no_title_validation`: blank and oversized titles accepted | 5 |
| `done_not_saved`: an edit returns success but is not saved | 3 |
| `no_security_headers`: security headers removed | 3 |

## Design

- **Isolated tests:** every test starts from freshly seeded data, so tests do not depend on each other.
- **Real server:** tests talk to the app over HTTP on a free local port instead of mocking it.
- **Page Object Model:** UI selectors live only in `tests/ui/pages.py`.
- **Evidence on failure:** an HTML report, plus a screenshot and Playwright trace for failed UI tests, uploaded as a CI artifact.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

pytest                      # all tests; the report is in reports/report.html
pytest -m security          # one layer: api, security or ui
pytest -m ui --headed       # watch the browser
python scripts/fault_check.py
python run_app.py           # try the app at http://127.0.0.1:5000
```

The accounts in `app/__init__.py` are fake and exist only for this demo.

## License

MIT

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

django-notes is a personal notes/bookmarks/tasks web app (single Django app: `notes`). Notes have a `type`
(`bookmark`, `task`, `idea`), can be tagged, and support recurring tasks, due dates/reminders, a weekly
schedule view, saved filters, and full-text search. It's designed for MySQL specifically (uses MySQL
`MATCH ... AGAINST` full-text search via raw SQL — see `CombinedSearchManager` in `notes/models.py`), so it
won't run correctly against SQLite/Postgres.

## Commands

Dependencies and virtualenv are managed with `uv`; the venv lives at `.venv`.

```bash
# install/sync dependencies (dev group has test/lint tooling)
uv sync --group dev

# run all tests (uses config.settings by default; local dev needs a MySQL DB configured
# in config/local_settings.py, which is gitignored)
.venv/bin/pytest

# run tests against the CI settings module (no local_settings.py required, reads DB_* env vars)
.venv/bin/pytest --ds=config.settings_ci

# run a single test file / test case / test method
.venv/bin/pytest tests/notes/views/test_home_view.py
.venv/bin/pytest tests/notes/views/test_home_view.py::HomeViewTests
.venv/bin/pytest tests/notes/views/test_home_view.py::HomeViewTests::test_shows_todays_tasks

# coverage (as run in CI)
.venv/bin/pytest --ds=config.settings_ci --cov --cov-report=xml --cov-report=term

# lint / format (ruff is also wired up as a pre-commit hook)
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/ruff check --fix .
.venv/bin/ruff format .

# docstring coverage/consistency (informational only, non-blocking in CI)
.venv/bin/interrogate -v notes/
.venv/bin/pydoclint notes/

# management commands (see notes/management/commands/)
.venv/bin/python manage.py cron               # runs the daily maintenance job (see below)
.venv/bin/python manage.py link_checker
.venv/bin/python manage.py clean_tags
.venv/bin/python manage.py merge_tags
.venv/bin/python manage.py replace_tag
.venv/bin/python manage.py build_tag_suggestions
.venv/bin/python manage.py old_notes
.venv/bin/python manage.py tag_diff
```

`cron.sh` (production, on the deploy host) and `cron-template.sh` (template for other environments) both just
invoke `manage.py cron` — that's the scheduled entry point that ties tag cleanup, tag-suggestion rebuilding,
and old-note pruning together (`notes/management/commands/cron.py`).

## Settings

- `config/settings.py` is the base settings module. It always ends by importing
  `config/local_settings.py` (gitignored, not present in a fresh checkout) for machine-specific overrides
  (DB credentials, `SECRET_KEY`, etc.) — without it Django will still boot (with a warning) but the DB config
  is an empty MySQL config, so most DB-touching commands will fail until `local_settings.py` is created.
- `config/settings_ci.py` extends the base settings and is what CI/tests actually run against — it reads
  `DB_HOST`/`DB_PORT`/`DB_USER`/`DB_PASSWORD`/`DB_NAME` from the environment and sets a throwaway
  `SECRET_KEY`. Prefer testing against this module rather than assuming a `local_settings.py` exists.
- `pyproject.toml`'s `[tool.pytest.ini_options]` sets `DJANGO_SETTINGS_MODULE = "config.settings"` as the
  default, so bare `pytest` needs a working `local_settings.py`; pass `--ds=config.settings_ci` to use the
  CI DB config instead.

## Architecture

- **Everything lives in one app, `notes/`.** Views are class-based (`notes/views.py`, one file, ~20 views),
  routed in `notes/urls.py` under the `notes:` namespace. There's no DRF/API layer beyond a small
  `TagAutocompleteView`.
- **Auth**: `notes.middleware.LoginRequiredMiddleware` makes the whole site login-required by default, with
  exemptions matched by regex against `settings.LOGIN_EXEMPT_URLS` (falls back to just `LOGIN_URL` if unset).
  Keep this in mind when adding a new URL that must be publicly accessible.
- **Per-user timezone handling**: `NotesProfile.timezone` stores each user's IANA timezone; "today" for a
  given user (used throughout the task/schedule views to decide what's due) is computed via
  `notes/utils.py::get_user_aware_date`/`get_user_aware_datetime`, not `django.utils.timezone.now()` directly.
  Falls back safely to Django's default timezone if the user is unauthenticated or has a bad/missing tz.
- **Tags & notes** are many-to-many through the explicit `NoteTag` model (`notes/models.py`), with a unique
  constraint on `(note, tag)`. `Tag.slug` is auto-generated via a custom `AutoSlugField`
  (`notes/fields.py`, wraps `django-autoslug`, defaults to `unique=True`).
- **Full-text search** (`CombinedSearchManager.combined_search`) is raw SQL using MySQL's `MATCH ... AGAINST`
  across note fields and tag name/slug, scoped to `user_id`. `CombinedSearch` is an unmanaged model that only
  exists to hang this manager off of. Because this is MySQL-specific raw SQL, tests that exercise search rely
  on a real MySQL DB (see `NotesTestCase` and CI's MySQL service container).
  There are corresponding fulltext-index migrations (`0017`, `0019`) — schema changes to searched columns
  should keep those indices in mind.
- **Recurring tasks**: `Note.get_next_due_date()` / `generate_next_task()` / `complete_task()` implement the
  recurrence lifecycle — completing a recurring task archives it and clones a new `Note` (via
  `model_to_dict`, stripping `id`/`tags`/`status`/`create_date`/`completed_date`) with the next due date, then
  re-attaches the same tags.
  A separate concept, `INACTIVE_NOTE_STATUSES` (`completed`, `archived`, `closed`), governs which notes count
  toward tag usage (`Tag.note_count()`) and are excluded by `clean_tags`.
- **`NotesConfig`** is a simple runtime key/value store (`NotesConfig.get_value(name)`), editable via the
  admin, for settings that live in the DB rather than in Django settings so they can change without a deploy.
  New keys are seeded via a data migration (see `0035_prefill_notesconfig.py`, `0036_important_notesconfig.py`,
  `0045_link_check_email_notesconfig.py` for the pattern). Known keys: `retain.days` (`cron`'s retention
  window for completed/closed/archived tasks), `schedule.important.tags` (used by `Note.has_important_tag()`
  alongside `priority == "high"`), `link_check.days` (`cron`'s staleness threshold, in days, before
  `link_checker` re-checks a link — see below), `link_check.email_enabled` (`"true"`/`"false"`, default off)
  and `link_check.email_recipients` (comma-separated email addresses, falls back to `settings.ADMINS` when
  blank) controlling whether/where `link_checker` emails its broken-link report.
- **Tag suggestions**: `notes/libs/association.py` + the `build_tag_suggestions` management command generate
  `TagSuggestion`/`TagSuggestionInputTag` rows (association-rule mining over co-occurring tags, via
  `mlxtend`) that feed tag autocomplete/suggestion UI.
- **Saved filters** (`SavedFilter`): stored tag/search combinations with an ordering; filtering itself goes
  through `notes/utils.py::get_filtered_notes`, which ANDs together notes matching *all* of a `+`-separated
  list of tag slugs (excludes `completed` status).
- **HTML content**: `Note.description` is a `tinymce.models.HTMLField`; output is sanitized via
  `notes/templatetags/sanitize.py` (built on `nh3`) rather than trusted as-is in templates.
- **Email**: `notes/utils.py::send_templated_mail(subject, template_name, context, recipient_list=None)` is
  the shared way to send email — it renders a matching `notes/templates/notes/emails/<template_name>.txt`
  and `.html` pair (the HTML ones extend `notes/emails/base.html`) and sends them as a multipart message via
  Django's standard `EMAIL_*` settings. Defaults `recipient_list` to `settings.ADMINS`. Any new outbound
  email should add a `.txt`/`.html` template pair under `notes/templates/notes/emails/` and call this helper
  rather than building `EmailMultiAlternatives` directly. `link_checker` is the first caller — it emails a
  report of broken/redirected links it finds (see below) and swallows `OSError`/`smtplib.SMTPException` so a
  misconfigured mail server doesn't fail the cron run.

## Tests

- `tests/` mirrors the `notes/` package layout (`tests/notes/views/`, `tests/notes/commands/`,
  `tests/notes/libs/`, `tests/notes/templatetags/`), plus `tests/notes/test_models.py` and
  `tests/notes/test_utils.py` at the top level for models/utils.
- `tests/base.py` defines `NotesTestCase`, the shared base class used across view tests: it creates a
  logged-in `self.user` plus an unrelated `self.other_user` (for cross-user isolation checks), and exposes
  `make_tag`/`make_note`/`make_task`/`tag_note` helpers. Prefer extending this over hand-rolling user/note
  setup in new tests.
- `tests/notes/commands/base.py` provides a similar shared base for management-command tests.
- Tests require a real MySQL database (no sqlite fallback) because of the raw-SQL full-text search and
  `utf8mb4`/collation-sensitive behavior — run with `--ds=config.settings_ci` and MySQL env vars set (see
  Commands above) unless `config/local_settings.py` is already configured locally.

## CI

GitHub Actions (`.github/workflows/workflow.yml`) runs against a MySQL 8.0 service container: `ruff check`,
`ruff format --check`, `pytest` with coverage (using `config.settings_ci`), then non-blocking
`interrogate`/`pydoclint` docstring reports, then a SonarCloud scan. Coverage/lint config lives in
`pyproject.toml` (`[tool.coverage.run]`, `[tool.ruff]`); Sonar config is in `sonar-project.properties`.

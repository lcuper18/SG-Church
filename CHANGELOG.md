# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing tagged as a release yet — all work so far lives on `main`. This
section reflects real history (from `git log`), not a plan.

#### Security
- Closed the member directory to plain members: list/detail of members,
  families and tags, the CSV export and the matching API endpoints now require
  a member-management role (admin, pastor, volunteer). Who is enrolled in a
  course or registered for an event is limited to staff; certificates can be
  opened only by their owner or staff
- Pastoral notes (members and families) are visible and editable only by admins
  and pastors, in the web UI and the API; a member's giving history on their
  page is limited to admins and treasurers
- The dashboard computes and shows member and giving figures only to the roles
  allowed to see them, and the menus hide sections a role cannot open

#### Added
- Attendance per site: a visitors head-count per event (non-members, saved from the attendance
  sheet and the API), a site filter and "Resumen por sede" in the attendance report (events, registered,
  members, visitors, total, average per event, members from another site), and CSV exports with
  visitors and site (new columns at the end) plus a per-site summary export
- Sites (sedes): a church can have several; each event belongs to one and members may have a
  home site. Configuración → Sedes (admins) to create, edit, deactivate or delete (blocked while
  in use). Single-site churches see no site fields at all. Event list/form/detail, member
  form/list filter/CSV export and import ("Sede" column), API (`/api/v1/sites/`, `?site=`),
  trash and audit are covered; existing events move to a "Sede principal"; the demo seed
  creates Central/Norte/Sur
- National ID on members ("Cédula" / DNI / RUT...): unique per church (formats like
  `1-1234-5678` and `112345678` are the same number), searchable, shown in list/detail/portal,
  in the CSV export and import (duplicates are detected by ID first), printed on PDF
  certificates, and shown only as its last digits in pickers and on the public check
  page. The label follows the church's country and can be renamed in Configuración. Audit
  entries record that it changed but never the number
- Block certificates as PDF (landscape Letter, ReportLab): church logo, the member's name,
  the block and its courses, issue date in Spanish, signer name/title (set in Configuración →
  Certificados), number and a QR to a public check page (`/education/certificates/verify/<number>/`)
  that confirms a printed copy is genuine without exposing anything not printed on it
- CSV import of members (Miembros → Importar CSV): loose header matching, `,` `;` and
  tab delimiters, UTF-8/Excel encodings, preview with per-row errors before saving,
  duplicate detection (skip or update), families and tags created on the fly, one
  audit line per import; also accepts our own export
- Audit trail (Bitácora, admins only): every create/change/delete/restore of members,
  families, tags, users, donations, expenses, courses, blocks, enrollments, events and
  the church settings, with who did it and a field-by-field diff (passwords and
  pastoral notes are recorded as changed but never shown)
- Trash (Papelera, admins only): deleting a member, family, event, course, block or
  expense hides it instead of destroying it; admins can restore it (with its
  enrolments, registrations and certificates) or remove it for good. Items are purged
  after `TRASH_RETENTION_DAYS` (90) by a nightly job. Donations are never deletable
- People pickers (register for an event, enrol in a course, choose a family's members)
  now search on demand through `/members/lookup/` instead of embedding every
  member in the page; the family form shows the chosen people as chips
- Member search ignores accents and matches every word, across name, e-mail and
  phone ("maria garcia" finds "María García"); backed by `Member.search_text`
- Nightly backups (database + uploaded files) run by a new Celery `beat` service:
  `pg_dump`/SQLite online backup, retention (`BACKUP_KEEP`), optional copy to an
  S3-compatible bucket, `manage.py backup_data` for manual runs; restore tested
  against PostgreSQL 16 (see docs/DEPLOYMENT.md)
- `/health/` now reports the database (503 when down) and Redis (200 `degraded`)
  as JSON
- `scripts/check.sh` (Django check, pending migrations, syntax errors, tests; local
  Python or Docker) and a versioned `pre-push` hook (`scripts/install-hooks.sh`),
  replacing a hosted CI service
- "Mi ficha" (/me/): every user sees their own record, courses, certificates,
  upcoming events and donations, and can update their contact details; admins
  link a login to a member record from the user form (or automatically by
  matching e-mail)
- Removed insecure fallback defaults for `SECRET_KEY`/`DATABASE_PASSWORD`
  (the app now fails to start instead of running with a guessable key or a
  known password); `DEBUG` no longer defaults to `True`
- Fixed the Stripe webhook, which was being rejected with 403 (missing
  CSRF exemption) — signature verification is the real trust boundary there
- Added file-extension and size validation on all file uploads (member
  photos, church logos, expense receipts)
- Enforced role-based access control (RBAC): `can_manage_finance`/
  `can_manage_members` are now actually checked in every web view and API
  endpoint — previously any authenticated user could mutate any tenant's
  members or financial data regardless of role

#### Fixed
- The audit trail stripped a trailing `_id` from every field name, which would have
  logged `national_id` in clear; field names now come from the model
- Removed N+1 queries: course-block progress (144 → 10 queries with 520 members),
  event list (37 → 6), family list (31 → 6), finance dashboard (32 → 8)
- Event list is paginated and shows upcoming events first; the donor report is
  paginated and its date range now includes the whole last day
- Treasurers no longer get links to the member page (403) from donation screens
- Replaced the multi-tenancy implementation: `TenantMiddleware` called
  `connection.set_schema()`, which doesn't exist on Django's standard
  Postgres backend (no schema-per-tenant library was ever installed) — it
  crashed on every request and was only kept alive by disabling the
  middleware in local dev. Isolation is now (and was already, in practice)
  row-level, via `tenant` foreign keys filtered on every query
  - Removed `tenants/provisioning.py` (dead code implementing the same
    broken schema-per-tenant approach, never called from anywhere)
- Fixed `setup.cfg`'s `[black]` section, which used TOML syntax invalid in
  an INI file — it broke `configparser` for every tool that reads
  `setup.cfg` (pytest, coverage.py, flake8) unless you passed `-c
  pytest.ini` by hand
- Fixed the Docker build silently swallowing `pip install` failures (`||
  true`), and switched the container entrypoint to `exec gunicorn` so it
  receives `SIGTERM` for a graceful shutdown
- Fixed `.env.example` documenting `DATABASE_URL`, a variable the app
  never actually reads (it reads `DATABASE_NAME`/`USER`/`PASSWORD`/`HOST`/
  `PORT` instead)
- Fixed the CI `build` job running `python -m build` with no packaging
  metadata anywhere in the repo (this ships as a Docker image, not a pip
  package) — it now builds the Docker image instead
- Removed a committed `test_db.sqlite3` and a stale Node/pnpm/Turbo CI
  workflow and monorepo config (`package.json`, `turbo.json`,
  `tsconfig*.json`) left over from before the pivot to Django
- Added missing migrations for the `notifications` and `emails` apps
  (their tables couldn't be created at all before this)

#### Added
- Multi-tenant architecture (row-level isolation) with Django Auth
- Role-based access control (RBAC): admin, treasurer, pastor, volunteer, member
- Church onboarding wizard (web) and `create_tenant`/`list_tenants`/
  `bootstrap_tenant` management commands
- Membership management: members, families, tags
- One-time donations via Stripe Checkout, with a verified webhook
- Expense tracking and a financial dashboard
- Email (Resend) and in-app notifications
- REST API (Django REST Framework) for members, families, tags, donations,
  expenses, campaigns, and notifications
- `sg_church/settings/standalone.py`: a zero-external-services deployment
  mode (SQLite, synchronous Celery) for a single church running its own
  instance, alongside the existing Postgres+Redis SaaS mode
- `docker-compose.standalone.yml` and `docker-compose.yml` for both
  deployment modes, verified end-to-end (build, migrate, bootstrap, login)

#### Infrastructure
- Django 5 setup with Python 3.12
- PostgreSQL (SaaS mode) or SQLite (standalone mode) via the Django ORM
- Django REST Framework for APIs
- Bootstrap 5 frontend
- Docker / Dokploy / VPS deployment configuration

---

## Future Releases

### [0.2.0] - Phase 2: Core Features (Planned)
- Sacrament records (Baptism)
- Recurring donation subscriptions
- Learning Management System (LMS)
- Advanced reporting and analytics
- SMS notifications
- Family grouping
- Attendance tracking

### [0.3.0] - Phase 3: Advanced Features (Planned)
- Learning paths and certifications
- Progressive Web App (PWA)
- Custom workflow automation
- Advanced analytics dashboard
- Mobile push notifications
- Payment method management
- Document management

### [0.4.0] - Phase 4: Scale & Polish (Planned)
- Performance optimization
- Public API for integrations
- Full internationalization (i18n)
- Native mobile apps (Flutter)
- AI-powered insights
- Advanced security features
- Compliance certifications

---

## Legend

- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` for vulnerability fixes
- `Infrastructure` for DevOps and infrastructure changes
- `Documentation` for documentation updates

---

*For detailed sprint-by-sprint progress, see [ROADMAP.md](./ROADMAP.md)*

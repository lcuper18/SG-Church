# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing tagged as a release yet — all work so far lives on `main`. This
section reflects real history (from `git log`), not a plan.

#### Security
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

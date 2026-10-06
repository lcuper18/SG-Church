#!/bin/sh
# `exec` replaces this shell with gunicorn (PID 1), so it receives SIGTERM
# directly and can shut down gracefully instead of being force-killed.
set -e

python manage.py migrate --noinput

# Opt-in demo data: set SEED_DEMO_DATA=true (optionally SEED_DEMO_TENANT=<subdomain>)
# to fill the tenant with fake people/finance/courses/events. Idempotent.
if [ "$SEED_DEMO_DATA" = "true" ]; then
    python manage.py seed_demo_data || echo "seed_demo_data failed (continuing boot)"
fi

# Opt-in extra user (e.g. a demo admin for a stakeholder): set EXTRA_USER_EMAIL
# plus optionally EXTRA_USER_FIRST_NAME/LAST_NAME/ROLE (default admin)/PASSWORD
# (random + printed to the logs if unset) and SEED_DEMO_TENANT. Idempotent.
if [ -n "$EXTRA_USER_EMAIL" ]; then
    python manage.py ensure_user "$EXTRA_USER_EMAIL" \
        --first-name "$EXTRA_USER_FIRST_NAME" --last-name "$EXTRA_USER_LAST_NAME" \
        --role "${EXTRA_USER_ROLE:-admin}" \
        ${SEED_DEMO_TENANT:+--tenant "$SEED_DEMO_TENANT"} \
        ${EXTRA_USER_PASSWORD:+--password "$EXTRA_USER_PASSWORD"} \
        || echo "ensure_user failed (continuing boot)"
fi

# Standalone (single-church) installs bootstrap their one tenant on first
# boot; the SaaS/hosted settings don't set this and skip it — churches sign
# up through the onboarding wizard instead.
if [ "$DJANGO_SETTINGS_MODULE" = "sg_church.settings.standalone" ]; then
    python manage.py bootstrap_tenant
fi

python manage.py collectstatic --noinput

exec gunicorn sg_church.wsgi:application --bind 0.0.0.0:8000

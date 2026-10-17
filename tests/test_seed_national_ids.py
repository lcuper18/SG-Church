"""The demo seed gives adults a unique, made-up cédula (and backfills older demos)."""

from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command

from members.models import Member


@pytest.mark.django_db(transaction=True)
def test_adults_get_unique_ids_children_do_not_and_reruns_fill_blanks(admin_user):
    tenant = admin_user.tenant
    call_command("seed_demo_data", tenant=tenant.subdomain, members=80, stdout=StringIO())

    seeded = Member.objects.filter(tenant=tenant)
    with_id = seeded.exclude(national_id="")
    keys = list(with_id.values_list("national_id_key", flat=True))
    assert keys and len(keys) == len(set(keys))
    assert all(len(m.national_id) == 11 and m.national_id.count("-") == 2 for m in with_id)
    assert not [m for m in seeded.filter(national_id="") if m.date_of_birth is None or
                (date.today() - m.date_of_birth).days >= 18 * 365]
    assert with_id.first().search_text.find(with_id.first().national_id_key.lower()) != -1

    # An older demo (seeded before the field existed) gets its IDs on the next run.
    seeded.update(national_id="", national_id_key="")
    out = StringIO()
    call_command("seed_demo_data", tenant=tenant.subdomain, stdout=out)
    assert f"National IDs filled in for {len(keys)} adults" in out.getvalue()

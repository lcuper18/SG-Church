from django.db import migrations


def give_every_church_a_main_site(apps, schema_editor):
    """Each church gets its "Sede principal", and its existing events go there."""
    Tenant = apps.get_model("tenants", "Tenant")
    Site = apps.get_model("tenants", "Site")
    Event = apps.get_model("events", "Event")
    for tenant in Tenant.objects.all():
        site = Site.objects.filter(tenant=tenant, is_main=True, deleted_at__isnull=True).first()
        if site is None:
            site = Site.objects.create(tenant=tenant, name="Sede principal", is_main=True)
        Event.objects.filter(tenant=tenant, site__isnull=True).update(site=site)


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0006_sites"),
        ("tenants", "0009_sites"),
    ]

    operations = [
        migrations.RunPython(give_every_church_a_main_site, migrations.RunPython.noop),
    ]

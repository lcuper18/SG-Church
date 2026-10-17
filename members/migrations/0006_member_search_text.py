from django.db import migrations, models

from core.text import fold


def fill_search_text(apps, schema_editor):
    """Give every existing member the accent-free text searches run against."""
    Member = apps.get_model("members", "Member")
    batch = []
    for member in Member.objects.iterator(chunk_size=500):
        member.search_text = fold(
            " ".join(
                str(value or "")
                for value in (member.first_name, member.last_name, member.email, member.phone)
            )
        )
        batch.append(member)
        if len(batch) >= 500:
            Member.objects.bulk_update(batch, ["search_text"])
            batch = []
    if batch:
        Member.objects.bulk_update(batch, ["search_text"])


class Migration(migrations.Migration):

    dependencies = [
        ("members", "0005_alter_member_gender_alter_member_marital_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="member",
            name="search_text",
            field=models.TextField(blank=True, default="", editable=False),
        ),
        migrations.RunPython(fill_search_text, migrations.RunPython.noop),
    ]

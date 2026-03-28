# Generated migration for Tag model and Member.tags change

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0002_tenant_church_fields"),
        ("members", "0001_initial"),
    ]

    operations = [
        # Create Tag model
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                (
                    "color",
                    models.CharField(
                        default="#3B82F6",
                        help_text="Hex color code (e.g., #3B82F6)",
                        max_length=7,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tags",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tag",
                "verbose_name_plural": "Tags",
                "db_table": "tags",
                "ordering": ["name"],
                "unique_together": {("tenant", "name")},
            },
        ),
        # Change Member.tags from JSONField to ManyToManyField
        migrations.RemoveField(
            model_name="member",
            name="tags",
        ),
        migrations.AddField(
            model_name="member",
            name="tags",
            field=models.ManyToManyField(
                blank=True, related_name="members", to="members.tag"
            ),
        ),
    ]

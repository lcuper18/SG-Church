# Generated migration for Tenant church fields

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="denomination",
            field=models.CharField(
                blank=True,
                choices=[
                    ("catholic", "Catholic"),
                    ("baptist", "Baptist"),
                    ("methodist", "Methodist"),
                    ("presbyterian", "Presbyterian"),
                    ("lutheran", "Lutheran"),
                    ("anglican", "Anglican"),
                    ("evangelical", "Evangelical"),
                    ("pentecostal", "Pentecostal"),
                    ("charismatic", "Charismatic"),
                    ("nondenominational", "Non-denominational"),
                    ("other", "Other"),
                ],
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="country",
            field=models.CharField(
                blank=True, help_text="ISO country code", max_length=2
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="city",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="tenant",
            name="state",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="tenant",
            name="logo",
            field=models.ImageField(blank=True, null=True, upload_to="church_logos/"),
        ),
        migrations.AddField(
            model_name="tenant",
            name="currency",
            field=models.CharField(
                choices=[
                    ("USD", "US Dollar"),
                    ("EUR", "Euro"),
                    ("MXN", "Mexican Peso"),
                    ("COP", "Colombian Peso"),
                    ("ARS", "Argentine Peso"),
                    ("BRL", "Brazilian Real"),
                    ("GBP", "British Pound"),
                    ("CAD", "Canadian Dollar"),
                    ("AUD", "Australian Dollar"),
                ],
                default="USD",
                max_length=3,
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="timezone",
            field=models.CharField(default="America/New_York", max_length=50),
        ),
        migrations.AddField(
            model_name="tenant",
            name="date_format",
            field=models.CharField(
                choices=[
                    ("DD/MM/YYYY", "DD/MM/YYYY"),
                    ("MM/DD/YYYY", "MM/DD/YYYY"),
                    ("YYYY-MM-DD", "YYYY-MM-DD"),
                ],
                default="DD/MM/YYYY",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="tenant",
            name="enable_families",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="tenant",
            name="enable_tags",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="tenant",
            name="onboarding_completed",
            field=models.BooleanField(default=False),
        ),
    ]

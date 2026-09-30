# Generated manually to match tenants/models.py (Tenant.logo validators)

import core.validators
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0004_alter_tenant_address_alter_tenant_stripe_account_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tenant',
            name='logo',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='church_logos/',
                validators=[
                    django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
                    core.validators.FileSizeValidator(max_mb=2),
                ],
            ),
        ),
    ]

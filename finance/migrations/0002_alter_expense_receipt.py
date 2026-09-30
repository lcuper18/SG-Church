# Generated manually to match finance/models.py (Expense.receipt validators)

import core.validators
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='receipt',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='expenses/receipts/',
                validators=[
                    django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']),
                    core.validators.FileSizeValidator(max_mb=10),
                ],
            ),
        ),
    ]

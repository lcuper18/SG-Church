# Generated manually to match members/models.py (Member.photo validators)

import core.validators
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0002_alter_user_managers'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='photo',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='members/photos/',
                validators=[
                    django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp']),
                    core.validators.FileSizeValidator(max_mb=5),
                ],
            ),
        ),
    ]

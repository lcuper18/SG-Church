# Generated manually to match notifications/models.py

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenants', '0004_alter_tenant_address_alter_tenant_stripe_account_id'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('notification_type', models.CharField(choices=[('donation_received', 'Donación Recibida'), ('expense_created', 'Gasto Creado'), ('expense_approved', 'Gasto Aprobado'), ('expense_rejected', 'Gasto Rechazado'), ('member_added', 'Nuevo Miembro'), ('member_updated', 'Miembro Actualizado'), ('system', 'Sistema')], max_length=50)),
                ('link', models.CharField(blank=True, default='', max_length=500)),
                ('content_type', models.CharField(blank=True, default='', max_length=50)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('is_read', models.BooleanField(default=False)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='tenants.tenant')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['tenant', 'user', '-created_at'], name='notif_tenant_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['tenant', 'is_read', '-created_at'], name='notif_tenant_read_created_idx'),
        ),
    ]

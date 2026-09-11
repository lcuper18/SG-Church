# Generated manually to match emails/models.py

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenants', '0004_alter_tenant_address_alter_tenant_stripe_account_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('to_email', models.EmailField(max_length=254)),
                ('to_name', models.CharField(blank=True, default='', max_length=255)),
                ('from_email', models.EmailField(max_length=254)),
                ('from_name', models.CharField(blank=True, default='', max_length=255)),
                ('subject', models.CharField(max_length=500)),
                ('template_name', models.CharField(blank=True, default='', max_length=100)),
                ('context', models.JSONField(blank=True, default=dict)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed'), ('bounced', 'Bounced')], default='pending', max_length=20)),
                ('error_message', models.TextField(blank=True, default='')),
                ('resend_message_id', models.CharField(blank=True, default='', max_length=100)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='email_logs', to='tenants.tenant')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='emaillog',
            index=models.Index(fields=['tenant', '-created_at'], name='emaillog_tenant_created_idx'),
        ),
        migrations.AddIndex(
            model_name='emaillog',
            index=models.Index(fields=['to_email', '-created_at'], name='emaillog_toemail_created_idx'),
        ),
        migrations.AddIndex(
            model_name='emaillog',
            index=models.Index(fields=['status'], name='emaillog_status_idx'),
        ),
    ]

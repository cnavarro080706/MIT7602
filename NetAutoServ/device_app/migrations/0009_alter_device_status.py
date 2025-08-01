# Generated by Django 4.2 on 2025-03-16 09:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('device_app', '0008_alter_device_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='status',
            field=models.CharField(blank=True, choices=[('active', 'Active'), ('under_deployment', 'Under Deployment'), ('decommissioned', 'Decommissioned')], default='under_deployment', max_length=20, null=True),
        ),
    ]

# Generated by Django 5.1.6 on 2025-03-02 16:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coderr_app', '0017_orders_delivery_time_in_days'),
    ]

    operations = [
        migrations.AddField(
            model_name='orders',
            name='features',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]

# Generated by Django 5.1.6 on 2025-02-26 19:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coderr_app', '0008_remove_offers_min_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='offers',
            name='min_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]

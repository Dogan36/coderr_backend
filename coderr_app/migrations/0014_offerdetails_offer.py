# Generated by Django 5.1.6 on 2025-02-28 12:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coderr_app', '0013_remove_offerdetails_offer'),
    ]

    operations = [
        migrations.AddField(
            model_name='offerdetails',
            name='offer',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='offer_details', to='coderr_app.offers'),
            preserve_default=False,
        ),
    ]

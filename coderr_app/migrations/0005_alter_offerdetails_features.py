# Generated by Django 5.1.6 on 2025-02-26 13:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coderr_app', '0004_alter_profil_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offerdetails',
            name='features',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]

# Generated by Django 5.1.6 on 2025-03-03 18:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coderr_app', '0022_alter_orders_features'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profil',
            old_name='type',
            new_name='profile_type',
        ),
    ]

# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-08-13 06:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mod_stats_by_aircraft', '0007_extra_ammo_breakdown_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='aircraftbucket',
            name='reset_ammo_breakdown_2',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='sortieaugmentation',
            name='recomputed_ammo_breakdown_2',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]

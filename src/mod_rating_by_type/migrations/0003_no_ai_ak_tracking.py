# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-02-13 11:13
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0036_pt_br'),
        ('mod_rating_by_type', '0002_personas'),
    ]

    operations = [
        migrations.CreateModel(
            name='VLifeAugmentation',
            fields=[
                ('vlife', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, related_name='VLifeAugmentation_MOD_SPLIT_RANKINGS', serialize=False, to='stats.VLife')),
                ('ak_no_ai', models.IntegerField(db_index=True, default=0)),
            ],
            options={
                'db_table': 'VLifeAugmentation_MOD_SPLIT_RANKINGS',
            },
        ),
        migrations.AddField(
            model_name='filteredvlife',
            name='ak_no_ai',
            field=models.IntegerField(db_index=True, default=0),
        ),
    ]

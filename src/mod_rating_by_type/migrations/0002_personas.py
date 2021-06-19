# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-06-19 09:40
from __future__ import unicode_literals

import django.contrib.postgres.fields
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import stats.models


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0036_pt_br'),
        ('mod_rating_by_type', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FilteredKillboard',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('won_1', models.IntegerField(default=0)),
                ('won_2', models.IntegerField(default=0)),
                ('wl_1', models.FloatField(default=0)),
                ('wl_2', models.FloatField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='FilteredPlayer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cls', models.CharField(blank=True, choices=[('light', 'light'), ('medium', 'medium'), ('heavy', 'heavy')], db_index=True, max_length=16)),
                ('type', models.CharField(choices=[('pilot', 'pilot'), ('gunner', 'gunner'), ('tankman', 'tankman')], db_index=True, default='pilot', max_length=8)),
                ('date_first_sortie', models.DateTimeField(null=True)),
                ('date_last_sortie', models.DateTimeField(null=True)),
                ('date_last_combat', models.DateTimeField(null=True)),
                ('score', models.BigIntegerField(db_index=True, default=0)),
                ('rating', models.BigIntegerField(db_index=True, default=0)),
                ('ratio', models.FloatField(default=1)),
                ('sorties_total', models.IntegerField(default=0)),
                ('sorties_coal', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(default=0), default=stats.models.default_coal_list, size=None)),
                ('sorties_cls', django.contrib.postgres.fields.jsonb.JSONField(default=stats.models.default_sorties_cls)),
                ('coal_pref', models.IntegerField(choices=[(0, 'neutral'), (1, 'Allies'), (2, 'Axis')], default=0)),
                ('flight_time', models.BigIntegerField(db_index=True, default=0)),
                ('ammo', django.contrib.postgres.fields.jsonb.JSONField(default=stats.models.default_ammo)),
                ('accuracy', models.FloatField(db_index=True, default=0)),
                ('streak_current', models.IntegerField(db_index=True, default=0)),
                ('streak_max', models.IntegerField(db_index=True, default=0)),
                ('score_streak_current', models.IntegerField(db_index=True, default=0)),
                ('score_streak_max', models.IntegerField(db_index=True, default=0)),
                ('streak_ground_current', models.IntegerField(db_index=True, default=0)),
                ('streak_ground_max', models.IntegerField(db_index=True, default=0)),
                ('sorties_streak_current', models.IntegerField(default=0)),
                ('sorties_streak_max', models.IntegerField(default=0)),
                ('ft_streak_current', models.IntegerField(default=0)),
                ('ft_streak_max', models.IntegerField(default=0)),
                ('sortie_max_ak', models.IntegerField(default=0)),
                ('sortie_max_gk', models.IntegerField(default=0)),
                ('lost_aircraft_current', models.IntegerField(default=0)),
                ('bailout', models.IntegerField(default=0)),
                ('wounded', models.IntegerField(default=0)),
                ('dead', models.IntegerField(default=0)),
                ('captured', models.IntegerField(default=0)),
                ('relive', models.IntegerField(default=0)),
                ('takeoff', models.IntegerField(default=0)),
                ('landed', models.IntegerField(default=0)),
                ('ditched', models.IntegerField(default=0)),
                ('crashed', models.IntegerField(default=0)),
                ('in_flight', models.IntegerField(default=0)),
                ('shotdown', models.IntegerField(default=0)),
                ('respawn', models.IntegerField(default=0)),
                ('disco', models.IntegerField(default=0)),
                ('ak_total', models.IntegerField(db_index=True, default=0)),
                ('ak_assist', models.IntegerField(default=0)),
                ('gk_total', models.IntegerField(db_index=True, default=0)),
                ('fak_total', models.IntegerField(default=0)),
                ('fgk_total', models.IntegerField(default=0)),
                ('killboard_pvp', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('killboard_pve', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('ce', models.FloatField(default=0)),
                ('kd', models.FloatField(db_index=True, default=0)),
                ('kl', models.FloatField(default=0)),
                ('ks', models.FloatField(default=0)),
                ('khr', models.FloatField(db_index=True, default=0)),
                ('gkd', models.FloatField(default=0)),
                ('gkl', models.FloatField(default=0)),
                ('gks', models.FloatField(default=0)),
                ('gkhr', models.FloatField(default=0)),
                ('wl', models.FloatField(default=0)),
                ('elo', models.FloatField(default=1000)),
                ('fairplay', models.IntegerField(default=100)),
                ('fairplay_time', models.IntegerField(default=0)),
                ('score_heavy', models.BigIntegerField(db_index=True, default=0)),
                ('score_medium', models.BigIntegerField(db_index=True, default=0)),
                ('score_light', models.BigIntegerField(db_index=True, default=0)),
                ('rating_heavy', models.BigIntegerField(db_index=True, default=0)),
                ('rating_medium', models.BigIntegerField(db_index=True, default=0)),
                ('rating_light', models.BigIntegerField(db_index=True, default=0)),
                ('flight_time_heavy', models.BigIntegerField(default=0)),
                ('flight_time_medium', models.BigIntegerField(default=0)),
                ('flight_time_light', models.BigIntegerField(default=0)),
                ('score_streak_current_heavy', models.IntegerField(db_index=True, default=0)),
                ('score_streak_current_medium', models.IntegerField(db_index=True, default=0)),
                ('score_streak_current_light', models.IntegerField(db_index=True, default=0)),
                ('score_streak_max_heavy', models.IntegerField(default=0)),
                ('score_streak_max_medium', models.IntegerField(default=0)),
                ('score_streak_max_light', models.IntegerField(default=0)),
                ('relive_heavy', models.IntegerField(default=0)),
                ('relive_medium', models.IntegerField(default=0)),
                ('relive_light', models.IntegerField(default=0)),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='stats.Profile')),
                ('squad', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='stats.Squad')),
                ('tour', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='stats.Tour')),
            ],
            options={
                'db_table': 'FilteredPlayer_MOD_SPLIT_RANKINGS',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='FilteredPlayerAircraft',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cls', models.CharField(blank=True, choices=[('light', 'light'), ('medium', 'medium'), ('heavy', 'heavy')], db_index=True, max_length=16)),
                ('score', models.IntegerField(default=0)),
                ('ratio', models.FloatField(default=1)),
                ('sorties_total', models.IntegerField(default=0)),
                ('flight_time', models.BigIntegerField(default=0)),
                ('ammo', django.contrib.postgres.fields.jsonb.JSONField(default=stats.models.default_ammo)),
                ('accuracy', models.FloatField(default=0)),
                ('bailout', models.IntegerField(default=0)),
                ('wounded', models.IntegerField(default=0)),
                ('dead', models.IntegerField(default=0)),
                ('captured', models.IntegerField(default=0)),
                ('relive', models.IntegerField(default=0)),
                ('takeoff', models.IntegerField(default=0)),
                ('landed', models.IntegerField(default=0)),
                ('ditched', models.IntegerField(default=0)),
                ('crashed', models.IntegerField(default=0)),
                ('in_flight', models.IntegerField(default=0)),
                ('shotdown', models.IntegerField(default=0)),
                ('respawn', models.IntegerField(default=0)),
                ('disco', models.IntegerField(default=0)),
                ('ak_total', models.IntegerField(default=0)),
                ('ak_assist', models.IntegerField(default=0)),
                ('gk_total', models.IntegerField(default=0)),
                ('fak_total', models.IntegerField(default=0)),
                ('fgk_total', models.IntegerField(default=0)),
                ('killboard_pvp', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('killboard_pve', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('ce', models.FloatField(default=0)),
                ('kd', models.FloatField(default=0)),
                ('kl', models.FloatField(default=0)),
                ('ks', models.FloatField(default=0)),
                ('khr', models.FloatField(default=0)),
                ('gkd', models.FloatField(default=0)),
                ('gkl', models.FloatField(default=0)),
                ('gks', models.FloatField(default=0)),
                ('gkhr', models.FloatField(default=0)),
                ('wl', models.FloatField(default=0)),
                ('aircraft', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='stats.Object')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='mod_rating_by_type.FilteredPlayer')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='stats.Profile')),
            ],
            options={
                'db_table': 'FilteredPlayerAircraft_MOD_SPLIT_RANKINGS',
            },
        ),
        migrations.CreateModel(
            name='FilteredPlayerMission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cls', models.CharField(blank=True, choices=[('light', 'light'), ('medium', 'medium'), ('heavy', 'heavy')], db_index=True, max_length=16)),
                ('score', models.IntegerField(db_index=True, default=0)),
                ('ratio', models.FloatField(default=1)),
                ('sorties_total', models.IntegerField(default=0)),
                ('sorties_coal', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(default=0), default=stats.models.default_coal_list, size=None)),
                ('coal_pref', models.IntegerField(choices=[(0, 'neutral'), (1, 'Allies'), (2, 'Axis')], default=0)),
                ('flight_time', models.BigIntegerField(db_index=True, default=0)),
                ('ammo', django.contrib.postgres.fields.jsonb.JSONField(default=stats.models.default_ammo)),
                ('accuracy', models.FloatField(db_index=True, default=0)),
                ('bailout', models.IntegerField(default=0)),
                ('wounded', models.IntegerField(default=0)),
                ('dead', models.IntegerField(default=0)),
                ('captured', models.IntegerField(default=0)),
                ('relive', models.IntegerField(default=0)),
                ('takeoff', models.IntegerField(default=0)),
                ('landed', models.IntegerField(default=0)),
                ('ditched', models.IntegerField(default=0)),
                ('crashed', models.IntegerField(default=0)),
                ('in_flight', models.IntegerField(default=0)),
                ('shotdown', models.IntegerField(default=0)),
                ('respawn', models.IntegerField(default=0)),
                ('disco', models.IntegerField(default=0)),
                ('ak_total', models.IntegerField(db_index=True, default=0)),
                ('ak_assist', models.IntegerField(default=0)),
                ('gk_total', models.IntegerField(db_index=True, default=0)),
                ('fak_total', models.IntegerField(default=0)),
                ('fgk_total', models.IntegerField(default=0)),
                ('killboard_pvp', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('killboard_pve', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('ce', models.FloatField(default=0)),
                ('kd', models.FloatField(db_index=True, default=0)),
                ('kl', models.FloatField(default=0)),
                ('ks', models.FloatField(default=0)),
                ('khr', models.FloatField(db_index=True, default=0)),
                ('gkd', models.FloatField(default=0)),
                ('gkl', models.FloatField(default=0)),
                ('gks', models.FloatField(default=0)),
                ('gkhr', models.FloatField(default=0)),
                ('wl', models.FloatField(default=0)),
                ('score_heavy', models.IntegerField(db_index=True, default=0)),
                ('score_medium', models.IntegerField(db_index=True, default=0)),
                ('score_light', models.IntegerField(db_index=True, default=0)),
                ('mission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='stats.Mission')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='mod_rating_by_type.FilteredPlayer')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='stats.Profile')),
            ],
            options={
                'db_table': 'FilteredPlayerMission_MOD_SPLIT_RANKINGS',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='FilteredReward',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('award', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stats.Award')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mod_rating_by_type.FilteredPlayer')),
            ],
            options={
                'verbose_name': 'reward',
                'verbose_name_plural': 'rewards',
                'db_table': 'FilteredRewards_MOD_SPLIT_RANKINGS',
            },
        ),
        migrations.CreateModel(
            name='FilteredVLife',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cls', models.CharField(blank=True, choices=[('light', 'light'), ('medium', 'medium'), ('heavy', 'heavy')], db_index=True, max_length=16)),
                ('date_first_sortie', models.DateTimeField(null=True)),
                ('date_last_sortie', models.DateTimeField(null=True)),
                ('date_last_combat', models.DateTimeField(null=True)),
                ('score', models.IntegerField(db_index=True, default=0)),
                ('ratio', models.FloatField(default=1)),
                ('sorties_total', models.IntegerField(db_index=True, default=0)),
                ('sorties_coal', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(default=0), default=stats.models.default_coal_list, size=None)),
                ('sorties_cls', django.contrib.postgres.fields.jsonb.JSONField(default=stats.models.default_sorties_cls)),
                ('coal_pref', models.IntegerField(choices=[(0, 'neutral'), (1, 'Allies'), (2, 'Axis')], default=0)),
                ('flight_time', models.BigIntegerField(db_index=True, default=0)),
                ('ammo', django.contrib.postgres.fields.jsonb.JSONField(default=stats.models.default_ammo)),
                ('accuracy', models.FloatField(db_index=True, default=0)),
                ('bailout', models.IntegerField(default=0)),
                ('wounded', models.IntegerField(default=0)),
                ('dead', models.IntegerField(default=0)),
                ('captured', models.IntegerField(default=0)),
                ('relive', models.IntegerField(db_index=True, default=0)),
                ('takeoff', models.IntegerField(default=0)),
                ('landed', models.IntegerField(default=0)),
                ('ditched', models.IntegerField(default=0)),
                ('crashed', models.IntegerField(default=0)),
                ('in_flight', models.IntegerField(default=0)),
                ('shotdown', models.IntegerField(default=0)),
                ('respawn', models.IntegerField(default=0)),
                ('disco', models.IntegerField(default=0)),
                ('ak_total', models.IntegerField(db_index=True, default=0)),
                ('ak_assist', models.IntegerField(default=0)),
                ('gk_total', models.IntegerField(db_index=True, default=0)),
                ('fak_total', models.IntegerField(default=0)),
                ('fgk_total', models.IntegerField(default=0)),
                ('killboard_pvp', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('killboard_pve', django.contrib.postgres.fields.jsonb.JSONField(default=dict)),
                ('status', models.CharField(choices=[('landed', 'landed'), ('ditched', 'ditched'), ('crashed', 'crashed'), ('shotdown', 'shotdown'), ('not_takeoff', 'not takeoff'), ('in_flight', 'in flight')], default='not_takeoff', max_length=12)),
                ('aircraft_status', models.CharField(choices=[('unharmed', 'unharmed'), ('damaged', 'damaged'), ('destroyed', 'destroyed')], default='unharmed', max_length=12)),
                ('bot_status', models.CharField(choices=[('healthy', 'healthy'), ('wounded', 'wounded'), ('dead', 'dead')], default='healthy', max_length=12)),
                ('ce', models.FloatField(default=0)),
                ('kl', models.FloatField(default=0)),
                ('ks', models.FloatField(default=0)),
                ('khr', models.FloatField(default=0)),
                ('gkl', models.FloatField(default=0)),
                ('gks', models.FloatField(default=0)),
                ('gkhr', models.FloatField(default=0)),
                ('wl', models.FloatField(default=0)),
                ('score_heavy', models.IntegerField(db_index=True, default=0)),
                ('score_medium', models.IntegerField(db_index=True, default=0)),
                ('score_light', models.IntegerField(db_index=True, default=0)),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='mod_rating_by_type.FilteredPlayer')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='stats.Profile')),
                ('tour', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='stats.Tour')),
            ],
            options={
                'db_table': 'FilteredVLife_MOD_SPLIT_RANKINGS',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='PlayerAugmentation',
            fields=[
                ('player', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, related_name='PlayerAugmentation_MOD_SPLIT_RANKINGS', serialize=False, to='stats.Player')),
                ('fighter_attacker_counter', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(-3), django.core.validators.MaxValueValidator(3)])),
            ],
            options={
                'db_table': 'Player_MOD_SPLIT_RANKINGS',
            },
        ),
        migrations.AddField(
            model_name='sortieaugmentation',
            name='computed_filter_player_killboard',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='sortieaugmentation',
            name='computed_filtered_player',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='sortieaugmentation',
            name='cls',
            field=models.CharField(blank=True, choices=[('heavy', 'heavy'), ('medium', 'medium'), ('light', 'light'), ('placeholder', 'placeholder')], db_index=True, max_length=16),
        ),
        migrations.AddField(
            model_name='filteredkillboard',
            name='player_1',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='mod_rating_by_type.FilteredPlayer'),
        ),
        migrations.AddField(
            model_name='filteredkillboard',
            name='player_2',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='stats.Player'),
        ),
        migrations.AlterUniqueTogether(
            name='filteredreward',
            unique_together=set([('award', 'player')]),
        ),
        migrations.AlterUniqueTogether(
            name='filteredplayermission',
            unique_together=set([('player', 'mission', 'cls')]),
        ),
        migrations.AlterUniqueTogether(
            name='filteredplayeraircraft',
            unique_together=set([('player', 'aircraft', 'cls')]),
        ),
        migrations.AlterUniqueTogether(
            name='filteredplayer',
            unique_together=set([('profile', 'type', 'tour', 'cls')]),
        ),
    ]

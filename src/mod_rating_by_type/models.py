from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Sum, Q, F
from stats.models import (Sortie, Player, VLife, PlayerMission, PlayerAircraft, Tour, Profile, default_coal_list, Award,
                          default_sorties_cls, default_ammo, rating_format_helper, calculate_rating, Mission, Object)
from mission_report.constants import Coalition, Country
from mission_report.statuses import BotLifeStatus, SortieStatus, LifeStatus, VLifeStatus
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.conf import settings
from stats.sql import get_position_by_field
from django.urls import reverse
from .config_modules import module_active, MODULE_SPLIT_RANKINGS


def get_profile_url(profile_id, nickname, tour_id, cls):
    url = '{url}?tour={tour_id}&cls={cls}'.format(url=reverse('stats:pilot', args=[profile_id, nickname]),
                                                  tour_id=tour_id, cls=cls)
    return url


def get_sorties_url(profile_id, nickname, tour_id, cls):
    url = '{url}?tour={tour_id}&cls={cls}'.format(
        url=reverse('stats:pilot_sorties', args=[profile_id, nickname]),
        tour_id=tour_id, cls=cls)
    return url


def get_vlifes_url(profile_id, nickname, tour_id, cls):
    url = '{url}?tour={tour_id}&cls={cls}'.format(
        url=reverse('stats:pilot_vlifes', args=[profile_id, nickname]),
        tour_id=tour_id, cls=cls)
    return url


def get_awards_url(profile_id, nickname, tour_id, cls):
    url = '{url}?tour={tour_id}&cls={cls}'.format(
        url=reverse('stats:pilot_awards', args=[profile_id, nickname]),
        tour_id=tour_id, cls=cls)
    return url


def get_killboard_url(profile_id, nickname, tour_id, cls):
    url = '{url}?tour={tour_id}&cls={cls}'.format(
        url=reverse('stats:pilot_killboard', args=[profile_id, nickname]),
        tour_id=tour_id, cls=cls)
    return url


# Monkey patched into Tour class of stats.models
def stats_summary_coal(self):
    summary_coal = {
        1: {'ak_total': 0, 'gk_total': 0, 'score': 0, 'flight_time': 0, 'light_flight_time': 0, 'medium_flight_time': 0,
            'heavy_flight_time': 0},
        2: {'ak_total': 0, 'gk_total': 0, 'score': 0, 'flight_time': 0, 'light_flight_time': 0, 'medium_flight_time': 0,
            'heavy_flight_time': 0},
    }
    _summary_coal = (Sortie.objects
                     .filter(tour_id=self.id, is_disco=False)
                     .values('coalition')
                     .order_by()
                     .annotate(ak_total=Sum('ak_total'), gk_total=Sum('gk_total'),
                               score=Sum('score'), flight_time_alias=Sum('flight_time')
                               ))
    if module_active(MODULE_SPLIT_RANKINGS):
        _summary_coal = _summary_coal.annotate(
            light_flight_time=models.Sum(
                models.Case(
                    models.When(aircraft__cls='aircraft_light', then=F('flight_time')),
                    default=0,
                    output_field=models.IntegerField()
                )),
            medium_flight_time=models.Sum(
                models.Case(
                    models.When(aircraft__cls='aircraft_medium', then=F('flight_time')),
                    default=0,
                    output_field=models.IntegerField()
                )),
            heavy_flight_time=models.Sum(
                models.Case(
                    models.When(aircraft__cls='aircraft_heavy', then=F('flight_time')),
                    default=0,
                    output_field=models.IntegerField()
                )),
        )

    for s in _summary_coal:
        summary_coal[s['coalition']].update(s)
        summary_coal[s['coalition']]['flight_time'] = s['flight_time_alias']
        print(s)

    return summary_coal


class SortieAugmentation(models.Model):
    """
    Additional fields to Sortie objects used by this mod.
    """
    sortie = models.OneToOneField(Sortie, on_delete=models.PROTECT, primary_key=True,
                                  related_name='SortieAugmentation_MOD_SPLIT_RANKINGS')

    CLASSES = (
        ('heavy', 'heavy'),
        ('medium', 'medium'),
        ('light', 'light'),
        ('placeholder', 'placeholder')
    )

    # This class differs from the cls found in a Sortie object.
    # Namely: Jabo flights are considred "medium", and P-38/Me-262 without bombs are considered "light"
    # In all other cases, it should be equal to the one found in
    cls = models.CharField(choices=CLASSES, max_length=16, blank=True, db_index=True)

    class Meta:
        # The long table name is to avoid any conflicts with new tables defined in the main branch of IL2 Stats.
        db_table = "Sortie_MOD_SPLIT_RANKINGS"


class PlayerAugmentation(models.Model):
    """
    Additional fields to Player objects used by this mod.
    """

    player = models.OneToOneField(Player, on_delete=models.PROTECT, primary_key=True,
                                  related_name='PlayerAugmentation_MOD_SPLIT_RANKINGS')

    # Between -3 and +3. +3 means last 3 jabo/attacker sorties were judged as fighters, -3 means judged as attackers.
    fighter_attacker_counter = models.IntegerField(default=0, validators=[MinValueValidator(-3), MaxValueValidator(3)])

    class Meta:
        # The long table name is to avoid any conflicts with new tables defined in the main branch of IL2 Stats.
        db_table = "Player_MOD_SPLIT_RANKINGS"

    def increment_attacker_plane_as_fighter(self):
        self.fighter_attacker_counter = min(self.fighter_attacker_counter + 1, 3)

    def increment_attacker_plane_as_attacker(self):
        self.fighter_attacker_counter = max(self.fighter_attacker_counter - 1, -3)

    def decide_ambiguous_fighter_attacker_sortie(self):
        if self.fighter_attacker_counter > 0:
            return 'light'
        elif self.fighter_attacker_counter < 0:
            return 'medium'
        else:
            return None


class FilteredPlayer(models.Model):
    """
    A copy of Player model from base IL2 Stats with added field "cls". Represents the fighter/attacker/bomber personas.

    Unfortunately model inheritance doesn't work here. It affects the queries of the base class, leading
    to lots of duplicate results when there should only be one.
    """
    LIGHT = 'light'
    MEDIUM = 'medium'
    HEAVY = 'heavy'
    CLASSES = (
        (LIGHT, 'light'),
        (MEDIUM, 'medium'),
        (HEAVY, 'heavy'),
    )
    cls = models.CharField(choices=CLASSES, max_length=16, blank=True, db_index=True)

    tour = models.ForeignKey(Tour, related_name='+', on_delete=models.CASCADE)
    PLAYER_TYPES = (
        ('pilot', 'pilot'),
        ('gunner', 'gunner'),
        ('tankman', 'tankman'),
    )
    type = models.CharField(choices=PLAYER_TYPES, max_length=8, default='pilot', db_index=True)
    profile = models.ForeignKey(Profile, related_name='+', on_delete=models.CASCADE)
    squad = models.ForeignKey('stats.Squad', related_name='+', blank=True, null=True, on_delete=models.SET_NULL)

    date_first_sortie = models.DateTimeField(null=True)
    date_last_sortie = models.DateTimeField(null=True)
    date_last_combat = models.DateTimeField(null=True)

    score = models.BigIntegerField(default=0, db_index=True)
    rating = models.BigIntegerField(default=0, db_index=True)
    ratio = models.FloatField(default=1)

    sorties_total = models.IntegerField(default=0)
    sorties_coal = ArrayField(models.IntegerField(default=0), default=default_coal_list)
    sorties_cls = JSONField(default=default_sorties_cls)

    COALITIONS = (
        (Coalition.neutral, pgettext_lazy('coalition', _('neutral'))),
        (Coalition.coal_1, settings.COAL_1_NAME),
        (Coalition.coal_2, settings.COAL_2_NAME),
    )

    coal_pref = models.IntegerField(default=Coalition.neutral, choices=COALITIONS)

    # налет в секундах?
    flight_time = models.BigIntegerField(default=0, db_index=True)

    ammo = JSONField(default=default_ammo)
    accuracy = models.FloatField(default=0, db_index=True)

    streak_current = models.IntegerField(default=0, db_index=True)
    streak_max = models.IntegerField(default=0)

    score_streak_current = models.IntegerField(default=0, db_index=True)
    score_streak_max = models.IntegerField(default=0)

    streak_ground_current = models.IntegerField(default=0, db_index=True)
    streak_ground_max = models.IntegerField(default=0)

    sorties_streak_current = models.IntegerField(default=0)
    sorties_streak_max = models.IntegerField(default=0)

    ft_streak_current = models.IntegerField(default=0)
    ft_streak_max = models.IntegerField(default=0)

    sortie_max_ak = models.IntegerField(default=0)
    sortie_max_gk = models.IntegerField(default=0)

    lost_aircraft_current = models.IntegerField(default=0)

    bailout = models.IntegerField(default=0)
    wounded = models.IntegerField(default=0)
    dead = models.IntegerField(default=0)
    captured = models.IntegerField(default=0)
    relive = models.IntegerField(default=0)

    takeoff = models.IntegerField(default=0)
    landed = models.IntegerField(default=0)
    ditched = models.IntegerField(default=0)
    crashed = models.IntegerField(default=0)
    in_flight = models.IntegerField(default=0)
    shotdown = models.IntegerField(default=0)

    respawn = models.IntegerField(default=0)
    disco = models.IntegerField(default=0)

    ak_total = models.IntegerField(default=0, db_index=True)
    ak_assist = models.IntegerField(default=0)
    gk_total = models.IntegerField(default=0, db_index=True)
    fak_total = models.IntegerField(default=0)
    fgk_total = models.IntegerField(default=0)

    killboard_pvp = JSONField(default=dict)
    killboard_pve = JSONField(default=dict)

    ce = models.FloatField(default=0)
    kd = models.FloatField(default=0, db_index=True)
    kl = models.FloatField(default=0)
    ks = models.FloatField(default=0)
    khr = models.FloatField(default=0, db_index=True)
    gkd = models.FloatField(default=0)
    gkl = models.FloatField(default=0)
    gks = models.FloatField(default=0)
    gkhr = models.FloatField(default=0)
    wl = models.FloatField(default=0)
    elo = models.FloatField(default=1000)

    fairplay = models.IntegerField(default=100)
    fairplay_time = models.IntegerField(default=0)

    # for mod pilots stats aircraft cls
    score_heavy = models.BigIntegerField(default=0, db_index=True)
    score_medium = models.BigIntegerField(default=0, db_index=True)
    score_light = models.BigIntegerField(default=0, db_index=True)
    rating_heavy = models.BigIntegerField(default=0, db_index=True)
    rating_medium = models.BigIntegerField(default=0, db_index=True)
    rating_light = models.BigIntegerField(default=0, db_index=True)
    flight_time_heavy = models.BigIntegerField(default=0)
    flight_time_medium = models.BigIntegerField(default=0)
    flight_time_light = models.BigIntegerField(default=0)
    score_streak_current_heavy = models.IntegerField(default=0, db_index=True)
    score_streak_current_medium = models.IntegerField(default=0, db_index=True)
    score_streak_current_light = models.IntegerField(default=0, db_index=True)
    score_streak_max_heavy = models.IntegerField(default=0)
    score_streak_max_medium = models.IntegerField(default=0)
    score_streak_max_light = models.IntegerField(default=0)
    relive_heavy = models.IntegerField(default=0)
    relive_medium = models.IntegerField(default=0)
    relive_light = models.IntegerField(default=0)

    class Meta:
        ordering = ['-id']
        db_table = "FilteredPlayer_MOD_SPLIT_RANKINGS"
        unique_together = (('profile', 'type', 'tour', 'cls'),)

    def __str__(self):
        return self.profile.nickname

    def save(self, *args, **kwargs):
        self.update_accuracy()
        self.update_analytics()
        self.update_rating()
        self.update_ratio()
        self.update_coal_pref()
        super().save(*args, **kwargs)

    def get_profile_url(self):
        return get_profile_url(self.profile_id, self.nickname, self.tour_id, self.cls)

    def get_base_profile_url(self):
        return get_profile_url(self.profile_id, self.nickname, self.tour_id, 'all   ')

    def get_light_profile_url(self):
        return get_profile_url(self.profile_id, self.nickname, self.tour_id, 'light')

    def get_medium_profile_url(self):
        return get_profile_url(self.profile_id, self.nickname, self.tour_id, 'medium')

    def get_heavy_profile_url(self):
        return get_profile_url(self.profile_id, self.nickname, self.tour_id, 'heavy')

    def get_sorties_url(self):
        return get_sorties_url(self.profile_id, self.nickname, self.tour_id, self.cls)

    def get_base_sorties_url(self):
        return get_sorties_url(self.profile_id, self.nickname, self.tour_id, 'all')

    def get_light_sorties_url(self):
        return get_sorties_url(self.profile_id, self.nickname, self.tour_id, 'light')

    def get_medium_sorties_url(self):
        return get_sorties_url(self.profile_id, self.nickname, self.tour_id, 'medium')

    def get_heavy_sorties_url(self):
        return get_sorties_url(self.profile_id, self.nickname, self.tour_id, 'heavy')

    def get_vlifes_url(self):
        return get_vlifes_url(self.profile_id, self.nickname, self.tour_id, self.cls)

    def get_base_vlifes_url(self):
        return get_vlifes_url(self.profile_id, self.nickname, self.tour_id, 'all')

    def get_light_vlifes_url(self):
        return get_vlifes_url(self.profile_id, self.nickname, self.tour_id, 'light')

    def get_medium_vlifes_url(self):
        return get_vlifes_url(self.profile_id, self.nickname, self.tour_id, 'medium')

    def get_heavy_vlifes_url(self):
        return get_vlifes_url(self.profile_id, self.nickname, self.tour_id, 'heavy')

    def get_awards_url(self):
        return get_awards_url(self.profile_id, self.nickname, self.tour_id, self.cls)

    def get_base_awards_url(self):
        return get_awards_url(self.profile_id, self.nickname, self.tour_id, 'all')

    def get_light_awards_url(self):
        return get_awards_url(self.profile_id, self.nickname, self.tour_id, 'light')

    def get_medium_awards_url(self):
        return get_awards_url(self.profile_id, self.nickname, self.tour_id, 'medium')

    def get_heavy_awards_url(self):
        return get_awards_url(self.profile_id, self.nickname, self.tour_id, 'heavy')

    def get_killboard_url(self):
        return get_killboard_url(self.profile_id, self.nickname, self.tour_id, self.cls)

    def get_base_killboard_url(self):
        return get_killboard_url(self.profile_id, self.nickname, self.tour_id, self.cls)

    def get_light_killboard_url(self):
        return get_killboard_url(self.profile_id, self.nickname, self.tour_id, 'light')

    def get_medium_killboard_url(self):
        return get_killboard_url(self.profile_id, self.nickname, self.tour_id, 'medium')

    def get_heavy_killboard_url(self):
        return get_killboard_url(self.profile_id, self.nickname, self.tour_id, 'heavy')

    # TODO: Get Aircraft overview working here as well.

    def get_position_by_field(self, field='rating'):
        return get_position_by_field(player=self, field=field)

    @property
    def nickname(self):
        return self.profile.nickname

    @property
    def lost_aircraft(self):
        return self.ditched + self.crashed + self.shotdown

    @property
    def not_takeoff(self):
        return self.sorties_total - self.takeoff

    @property
    def flight_time_hours(self):
        return self.flight_time / 3600

    @property
    def flight_time_light_hours(self):
        return self.flight_time_light / 3600

    @property
    def flight_time_medium_hours(self):
        return self.flight_time_medium / 3600

    @property
    def flight_time_heavy_hours(self):
        return self.flight_time_heavy / 3600

    @property
    def rating_format(self):
        return rating_format_helper(self.rating)

    @property
    def rating_format_heavy(self):
        return rating_format_helper(self.rating_heavy)

    @property
    def rating_format_medium(self):
        return rating_format_helper(self.rating_medium)

    @property
    def rating_format_light(self):
        return rating_format_helper(self.rating_light)

    @property
    def ak_total_ai(self):
        aircraft_light = self.killboard_pve.get('aircraft_light', 0)
        aircraft_medium = self.killboard_pve.get('aircraft_medium', 0)
        aircraft_heavy = self.killboard_pve.get('aircraft_heavy', 0)
        aircraft_transport = self.killboard_pve.get('aircraft_transport', 0)
        return aircraft_light + aircraft_medium + aircraft_heavy + aircraft_transport

    def update_accuracy(self):
        if self.ammo['used_cartridges']:
            self.accuracy = round(self.ammo['hit_bullets'] * 100 / self.ammo['used_cartridges'], 1)

    def update_analytics(self):
        self.kd = round(self.ak_total / max(self.relive, 1), 2)
        self.kl = round(self.ak_total / max(self.lost_aircraft, 1), 2)
        self.ks = round(self.ak_total / max(self.sorties_total, 1), 2)
        self.khr = round(self.ak_total / max(self.flight_time_hours, 1), 2)
        self.gkd = round(self.gk_total / max(self.relive, 1), 2)
        self.gkl = round(self.gk_total / max(self.lost_aircraft, 1), 2)
        self.gks = round(self.gk_total / max(self.sorties_total, 1), 2)
        self.gkhr = round(self.gk_total / max(self.flight_time_hours, 1), 2)
        self.wl = round(self.ak_total / max(self.shotdown, 1), 2)
        self.ce = round(self.kl * self.khr / 10, 2)

    def update_rating(self):
        self.rating = calculate_rating(self.score, self.relive, self.flight_time_hours)
        self.rating_light = calculate_rating(self.score_light, self.relive_light, self.flight_time_light_hours)
        self.rating_medium = calculate_rating(self.score_medium, self.relive_medium, self.flight_time_medium_hours)
        self.rating_heavy = calculate_rating(self.score_heavy, self.relive_heavy, self.flight_time_heavy_hours)

    def update_ratio(self):
        ratio = Sortie.objects.filter(player_id=self.id).aggregate(ratio=Avg('ratio'))['ratio']
        if ratio:
            self.ratio = round(ratio, 2)

    def update_coal_pref(self):
        if self.sorties_total:
            coal_1 = round(self.sorties_coal[1] * 100 / self.sorties_total, 0)
            if coal_1 > 60:
                self.coal_pref = 1
            elif coal_1 < 40:
                self.coal_pref = 2
            else:
                self.coal_pref = 0


class FilteredVLife(models.Model):
    """
    A copy of VLife model from base IL2 Stats with added field "cls". Represents the fighter/attacker/bomber personas.

    Unfortunately model inheritance doesn't work here. It affects the queries of the base class, leading
    to lots of duplicate results when there should only be one.
    """
    LIGHT = 'light'
    MEDIUM = 'medium'
    HEAVY = 'heavy'
    CLASSES = (
        (LIGHT, 'light'),
        (MEDIUM, 'medium'),
        (HEAVY, 'heavy'),
    )
    cls = models.CharField(choices=CLASSES, max_length=16, blank=True, db_index=True)

    profile = models.ForeignKey(Profile, related_name='+', on_delete=models.CASCADE)
    player = models.ForeignKey(FilteredPlayer, related_name='+', on_delete=models.CASCADE)
    tour = models.ForeignKey(Tour, related_name='+', on_delete=models.CASCADE)

    date_first_sortie = models.DateTimeField(null=True)
    date_last_sortie = models.DateTimeField(null=True)
    date_last_combat = models.DateTimeField(null=True)

    score = models.IntegerField(default=0, db_index=True)
    ratio = models.FloatField(default=1)

    sorties_total = models.IntegerField(default=0, db_index=True)
    sorties_coal = ArrayField(models.IntegerField(default=0), default=default_coal_list)
    sorties_cls = JSONField(default=default_sorties_cls)

    COALITIONS = (
        (Coalition.neutral, pgettext_lazy('coalition', _('neutral'))),
        (Coalition.coal_1, settings.COAL_1_NAME),
        (Coalition.coal_2, settings.COAL_2_NAME),
    )

    coal_pref = models.IntegerField(default=Coalition.neutral, choices=COALITIONS)

    flight_time = models.BigIntegerField(default=0, db_index=True)

    ammo = JSONField(default=default_ammo)
    accuracy = models.FloatField(default=0, db_index=True)

    bailout = models.IntegerField(default=0)
    wounded = models.IntegerField(default=0)
    dead = models.IntegerField(default=0)
    captured = models.IntegerField(default=0)
    relive = models.IntegerField(default=0, db_index=True)

    takeoff = models.IntegerField(default=0)
    landed = models.IntegerField(default=0)
    ditched = models.IntegerField(default=0)
    crashed = models.IntegerField(default=0)
    in_flight = models.IntegerField(default=0)
    shotdown = models.IntegerField(default=0)

    respawn = models.IntegerField(default=0)
    disco = models.IntegerField(default=0)

    ak_total = models.IntegerField(default=0, db_index=True)
    ak_assist = models.IntegerField(default=0)
    gk_total = models.IntegerField(default=0, db_index=True)
    fak_total = models.IntegerField(default=0)
    fgk_total = models.IntegerField(default=0)

    killboard_pvp = JSONField(default=dict)
    killboard_pve = JSONField(default=dict)

    STATUS = (
        (SortieStatus.landed, pgettext_lazy('sortie_status', 'landed')),
        (SortieStatus.ditched, pgettext_lazy('sortie_status', 'ditched')),
        (SortieStatus.crashed, pgettext_lazy('sortie_status', 'crashed')),
        (SortieStatus.shotdown, pgettext_lazy('sortie_status', 'shotdown')),
        (SortieStatus.not_takeoff, pgettext_lazy('sortie_status', 'not takeoff')),
        (SortieStatus.in_flight, pgettext_lazy('sortie_status', 'in flight')),
    )

    status = models.CharField(max_length=12, choices=STATUS, default=SortieStatus.not_takeoff)

    AIRCRAFT_STATUS = (
        (LifeStatus.unharmed, pgettext_lazy('aircraft_status', 'unharmed')),
        (LifeStatus.damaged, pgettext_lazy('aircraft_status', 'damaged')),
        (LifeStatus.destroyed, pgettext_lazy('aircraft_status', 'destroyed')),
    )

    aircraft_status = models.CharField(max_length=12, choices=AIRCRAFT_STATUS, default=LifeStatus.unharmed)

    BOT_STATUS = (
        (BotLifeStatus.healthy, pgettext_lazy('sortie_status', 'healthy')),
        (BotLifeStatus.wounded, pgettext_lazy('sortie_status', 'wounded')),
        (BotLifeStatus.dead, pgettext_lazy('sortie_status', 'dead')),
    )

    bot_status = models.CharField(max_length=12, choices=BOT_STATUS, default=BotLifeStatus.healthy)

    ce = models.FloatField(default=0)
    kl = models.FloatField(default=0)
    ks = models.FloatField(default=0)
    khr = models.FloatField(default=0)
    gkl = models.FloatField(default=0)
    gks = models.FloatField(default=0)
    gkhr = models.FloatField(default=0)
    wl = models.FloatField(default=0)

    # for mod pilots stats aircraft cls
    score_heavy = models.IntegerField(default=0, db_index=True)
    score_medium = models.IntegerField(default=0, db_index=True)
    score_light = models.IntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['-id']
        db_table = "FilteredVLife_MOD_SPLIT_RANKINGS"

    def __str__(self):
        return self.profile.nickname

    def save(self, *args, **kwargs):
        self.update_accuracy()
        self.update_analytics()
        self.update_ratio()
        self.update_coal_pref()
        super().save(*args, **kwargs)

    @property
    def is_dead(self):
        return self.bot_status == BotLifeStatus.dead

    @property
    def is_healthy(self):
        return self.bot_status == BotLifeStatus.healthy

    @property
    def is_wounded(self):
        return self.bot_status == BotLifeStatus.wounded

    @property
    def is_not_takeoff(self):
        return self.status == SortieStatus.not_takeoff

    @property
    def is_landed(self):
        return self.status == SortieStatus.landed

    @property
    def is_in_flight(self):
        return self.status == SortieStatus.in_flight

    @property
    def is_ditched(self):
        return self.status == SortieStatus.ditched

    @property
    def is_captured(self):
        return self.captured

    @property
    def is_crashed(self):
        return self.status == SortieStatus.crashed

    @property
    def is_shotdown(self):
        return self.status == SortieStatus.shotdown

    @property
    def is_lost_aircraft(self):
        return self.is_ditched or self.is_crashed or self.is_shotdown

    @property
    def nickname(self):
        return self.profile.nickname

    @property
    def lost_aircraft(self):
        return self.ditched + self.crashed + self.shotdown

    @property
    def flight_time_hours(self):
        return self.flight_time / 3600

    @property
    def ak_total_ai(self):
        aircraft_light = self.killboard_pve.get('aircraft_light', 0)
        aircraft_medium = self.killboard_pve.get('aircraft_medium', 0)
        aircraft_heavy = self.killboard_pve.get('aircraft_heavy', 0)
        aircraft_transport = self.killboard_pve.get('aircraft_transport', 0)
        return aircraft_light + aircraft_medium + aircraft_heavy + aircraft_transport

    def update_accuracy(self):
        if self.ammo['used_cartridges']:
            self.accuracy = round(self.ammo['hit_bullets'] * 100 / self.ammo['used_cartridges'], 1)

    def update_analytics(self):
        self.kl = round(self.ak_total / max(self.lost_aircraft, 1), 2)
        self.ks = round(self.ak_total / max(self.sorties_total, 1), 2)
        self.khr = round(self.ak_total / max(self.flight_time_hours, 1), 2)
        self.gkl = round(self.gk_total / max(self.lost_aircraft, 1), 2)
        self.gks = round(self.gk_total / max(self.sorties_total, 1), 2)
        self.gkhr = round(self.gk_total / max(self.flight_time_hours, 1), 2)
        self.wl = round(self.ak_total / max(self.shotdown, 1), 2)
        self.ce = round(self.kl * self.khr / 10, 2)

    def update_ratio(self):
        ratio = (Sortie.objects.filter(player_id=self.id, vlife_id=self.id)
            .aggregate(ratio=Avg('ratio'))['ratio'])
        if ratio:
            self.ratio = round(ratio, 2)

    def update_coal_pref(self):
        if self.sorties_total:
            coal_1 = round(self.sorties_coal[1] * 100 / self.sorties_total, 0)
            if coal_1 > 60:
                self.coal_pref = 1
            elif coal_1 < 40:
                self.coal_pref = 2
            else:
                self.coal_pref = 0


class FilteredPlayerMission(models.Model):
    """
    A copy of PlayerMission model from base IL2 Stats with added field "cls".
    Represents the fighter/attacker/bomber personas.

    Unfortunately model inheritance doesn't work here. It affects the queries of the base class, leading
    to lots of duplicate results when there should only be one.
    """

    LIGHT = 'light'
    MEDIUM = 'medium'
    HEAVY = 'heavy'
    CLASSES = (
        (LIGHT, 'light'),
        (MEDIUM, 'medium'),
        (HEAVY, 'heavy'),
    )
    cls = models.CharField(choices=CLASSES, max_length=16, blank=True, db_index=True)

    profile = models.ForeignKey(Profile, related_name='+', on_delete=models.CASCADE)
    player = models.ForeignKey(FilteredPlayer, related_name='+', on_delete=models.CASCADE)
    mission = models.ForeignKey(Mission, related_name='+', on_delete=models.CASCADE)

    score = models.IntegerField(default=0, db_index=True)
    ratio = models.FloatField(default=1)

    sorties_total = models.IntegerField(default=0)
    sorties_coal = ArrayField(models.IntegerField(default=0), default=default_coal_list)

    COALITIONS = (
        (Coalition.neutral, pgettext_lazy('coalition', _('neutral'))),
        (Coalition.coal_1, settings.COAL_1_NAME),
        (Coalition.coal_2, settings.COAL_2_NAME),
    )

    coal_pref = models.IntegerField(default=Coalition.neutral, choices=COALITIONS)

    # налет в секундах?
    flight_time = models.BigIntegerField(default=0, db_index=True)

    ammo = JSONField(default=default_ammo)
    accuracy = models.FloatField(default=0, db_index=True)

    bailout = models.IntegerField(default=0)
    wounded = models.IntegerField(default=0)
    dead = models.IntegerField(default=0)
    captured = models.IntegerField(default=0)
    relive = models.IntegerField(default=0)

    takeoff = models.IntegerField(default=0)
    landed = models.IntegerField(default=0)
    ditched = models.IntegerField(default=0)
    crashed = models.IntegerField(default=0)
    in_flight = models.IntegerField(default=0)
    shotdown = models.IntegerField(default=0)

    respawn = models.IntegerField(default=0)
    disco = models.IntegerField(default=0)

    ak_total = models.IntegerField(default=0, db_index=True)
    ak_assist = models.IntegerField(default=0)
    gk_total = models.IntegerField(default=0, db_index=True)
    fak_total = models.IntegerField(default=0)
    fgk_total = models.IntegerField(default=0)

    killboard_pvp = JSONField(default=dict)
    killboard_pve = JSONField(default=dict)

    ce = models.FloatField(default=0)
    kd = models.FloatField(default=0, db_index=True)
    kl = models.FloatField(default=0)
    ks = models.FloatField(default=0)
    khr = models.FloatField(default=0, db_index=True)
    gkd = models.FloatField(default=0)
    gkl = models.FloatField(default=0)
    gks = models.FloatField(default=0)
    gkhr = models.FloatField(default=0)
    wl = models.FloatField(default=0)

    # for mod pilots stats aircraft cls
    score_heavy = models.IntegerField(default=0, db_index=True)
    score_medium = models.IntegerField(default=0, db_index=True)
    score_light = models.IntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['-id']
        db_table = "FilteredPlayerMission_MOD_SPLIT_RANKINGS"
        unique_together = (('player', 'mission', 'cls'),)

    def __str__(self):
        return self.profile.nickname

    def save(self, *args, **kwargs):
        self.update_accuracy()
        self.update_analytics()
        self.update_ratio()
        self.update_coal_pref()
        super().save(*args, **kwargs)

    def get_profile_url(self):
        url = '{url}?tour={tour_id}'.format(url=reverse('stats:pilot', args=[self.profile_id, self.nickname]),
                                            tour_id=self.player.tour_id)
        return url

    @property
    def nickname(self):
        return self.profile.nickname

    @property
    def lost_aircraft(self):
        return self.ditched + self.crashed + self.shotdown

    @property
    def flight_time_hours(self):
        return self.flight_time / 3600

    def update_accuracy(self):
        if self.ammo['used_cartridges']:
            self.accuracy = round(self.ammo['hit_bullets'] * 100 / self.ammo['used_cartridges'], 1)

    def update_analytics(self):
        self.kd = round(self.ak_total / max(self.relive, 1), 2)
        self.kl = round(self.ak_total / max(self.lost_aircraft, 1), 2)
        self.ks = round(self.ak_total / max(self.sorties_total, 1), 2)
        self.khr = round(self.ak_total / max(self.flight_time_hours, 1), 2)
        self.gkd = round(self.gk_total / max(self.relive, 1), 2)
        self.gkl = round(self.gk_total / max(self.lost_aircraft, 1), 2)
        self.gks = round(self.gk_total / max(self.sorties_total, 1), 2)
        self.gkhr = round(self.gk_total / max(self.flight_time_hours, 1), 2)
        self.wl = round(self.ak_total / max(self.shotdown, 1), 2)
        self.ce = round(self.kl * self.khr / 10, 2)

    def update_ratio(self):
        ratio = (Sortie.objects.filter(player_id=self.id, mission_id=self.mission_id)
            .aggregate(ratio=Avg('ratio'))['ratio'])
        if ratio:
            self.ratio = round(ratio, 2)

    def update_coal_pref(self):
        if self.sorties_total:
            coal_1 = round(self.sorties_coal[1] * 100 / self.sorties_total, 0)
            if coal_1 > 60:
                self.coal_pref = 1
            elif coal_1 < 40:
                self.coal_pref = 2
            else:
                self.coal_pref = 0


class FilteredPlayerAircraft(models.Model):
    """
    A copy of PlayerMission model from base IL2 Stats with added field "cls".
    Represents the fighter/attacker/bomber personas.

    Unfortunately model inheritance doesn't work here. It affects the queries of the base class, leading
    to lots of duplicate results when there should only be one.
    """
    LIGHT = 'light'
    MEDIUM = 'medium'
    HEAVY = 'heavy'
    CLASSES = (
        (LIGHT, 'light'),
        (MEDIUM, 'medium'),
        (HEAVY, 'heavy'),
    )
    cls = models.CharField(choices=CLASSES, max_length=16, blank=True, db_index=True)

    profile = models.ForeignKey(Profile, related_name='+', on_delete=models.CASCADE)
    player = models.ForeignKey(FilteredPlayer, related_name='+', on_delete=models.CASCADE)
    aircraft = models.ForeignKey(Object, related_name='+', on_delete=models.PROTECT)

    score = models.IntegerField(default=0)
    ratio = models.FloatField(default=1)

    sorties_total = models.IntegerField(default=0)
    flight_time = models.BigIntegerField(default=0)

    ammo = JSONField(default=default_ammo)
    accuracy = models.FloatField(default=0)

    bailout = models.IntegerField(default=0)
    wounded = models.IntegerField(default=0)
    dead = models.IntegerField(default=0)
    captured = models.IntegerField(default=0)
    relive = models.IntegerField(default=0)

    takeoff = models.IntegerField(default=0)
    landed = models.IntegerField(default=0)
    ditched = models.IntegerField(default=0)
    crashed = models.IntegerField(default=0)
    in_flight = models.IntegerField(default=0)
    shotdown = models.IntegerField(default=0)

    respawn = models.IntegerField(default=0)
    disco = models.IntegerField(default=0)

    ak_total = models.IntegerField(default=0)
    ak_assist = models.IntegerField(default=0)
    gk_total = models.IntegerField(default=0)
    fak_total = models.IntegerField(default=0)
    fgk_total = models.IntegerField(default=0)

    killboard_pvp = JSONField(default=dict)
    killboard_pve = JSONField(default=dict)

    ce = models.FloatField(default=0)
    kd = models.FloatField(default=0)
    kl = models.FloatField(default=0)
    ks = models.FloatField(default=0)
    khr = models.FloatField(default=0)
    gkd = models.FloatField(default=0)
    gkl = models.FloatField(default=0)
    gks = models.FloatField(default=0)
    gkhr = models.FloatField(default=0)
    wl = models.FloatField(default=0)

    class Meta:
        # ordering = ['-id']
        db_table = "FilteredPlayerAircraft_MOD_SPLIT_RANKINGS"
        unique_together = (('player', 'aircraft', 'cls'),)

    def __str__(self):
        return '{nickname} [{aircraft}]'.format(nickname=self.profile.nickname, aircraft=self.aircraft.name)

    @property
    def nickname(self):
        return self.profile.nickname

    @property
    def lost_aircraft(self):
        return self.ditched + self.crashed + self.shotdown

    @property
    def flight_time_hours(self):
        return self.flight_time / 3600

    def save(self, *args, **kwargs):
        self.update_accuracy()
        self.update_analytics()
        self.update_ratio()
        super().save(*args, **kwargs)

    def update_accuracy(self):
        if self.ammo['used_cartridges']:
            self.accuracy = round(self.ammo['hit_bullets'] * 100 / self.ammo['used_cartridges'], 1)

    def update_analytics(self):
        self.kd = round(self.ak_total / max(self.relive, 1), 2)
        self.kl = round(self.ak_total / max(self.lost_aircraft, 1), 2)
        self.ks = round(self.ak_total / max(self.sorties_total, 1), 2)
        self.khr = round(self.ak_total / max(self.flight_time_hours, 1), 2)
        self.gkd = round(self.gk_total / max(self.relive, 1), 2)
        self.gkl = round(self.gk_total / max(self.lost_aircraft, 1), 2)
        self.gks = round(self.gk_total / max(self.sorties_total, 1), 2)
        self.gkhr = round(self.gk_total / max(self.flight_time_hours, 1), 2)
        self.wl = round(self.ak_total / max(self.shotdown, 1), 2)
        self.ce = round(self.kl * self.khr / 10, 2)

    def update_ratio(self):
        ratio = (Sortie.objects.filter(player_id=self.id, aircraft_id=self.aircraft_id)
            .aggregate(ratio=Avg('ratio'))['ratio'])
        if ratio:
            self.ratio = round(ratio, 2)


class FilteredReward(models.Model):
    """
    Copy of Reward which uses FilteredPlayer instead of Player. Medals for fighter/attacker/bomber personas.

    Django model inheritance doesn't work here because it doesn't work for FilteredPlayer.
    """
    award = models.ForeignKey(Award, on_delete=models.CASCADE)
    player = models.ForeignKey(FilteredPlayer, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'FilteredRewards_MOD_SPLIT_RANKINGS'
        unique_together = (('award', 'player'),)
        verbose_name = _('reward')
        verbose_name_plural = _('rewards')

    def __str__(self):
        return '{player} - {award}'.format(player=self.player, award=self.award)

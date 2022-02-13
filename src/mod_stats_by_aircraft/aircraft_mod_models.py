from django.db import models
from stats.models import Tour, Object, Sortie, rating_format_helper, Player
from mission_report.constants import Coalition
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.conf import settings
from django.urls import reverse

from .reservoir_sampling import SAMPLE, RESERVOIR_COUNTER, update_reservoir
from .variant_utils import has_bomb_variant, has_juiced_variant
import math

TOTALS = 'totals'
AVERAGES = 'avg'
CANNON = 'cannon'
MACHINE_GUN = 'mg'
CANNON_MG = 'all'
RECEIVED = 'received'
GIVEN = 'given'
INST = 'instances'
PILOT_KILLS = 'pilot_kills'
COUNT = 'count'
M2 = 'm2'  # For Welford's online algorithm to compute variance.
STANDARD_DEVIATION = 'std'


def default_ammo_breakdown():
    return {
        GIVEN: {
            TOTALS: dict(),
            AVERAGES: dict(),
        },
        RECEIVED: {
            TOTALS: dict(),
            AVERAGES: dict(),
        },
    }


def compute_float(numerator, denominator, round_to=2):
    return round(numerator / max(denominator, 1), round_to)


def percent_format(percent, total):
    return '{value}% ({total})'.format(value=percent, total=total)


class AircraftBucket(models.Model):
    # ========================= CHOICES
    NO_FILTER = 'NO_FILTER'
    NO_BOMBS_NO_JUICE = 'NO_BOMBS_JUICE'
    BOMBS = 'BOMBS'  # Without Juice
    JUICED = 'JUICE'  # Without Bombs
    ALL = 'ALL'  # Bombs and juice

    filter_choices = [
        (NO_FILTER, 'no filter'),
        (NO_BOMBS_NO_JUICE, 'no bombs nor juice'),
        (BOMBS, 'bomb sorties only with no juice'),
        (JUICED, 'juiced (upgraded engine/fuel)'),
        (ALL, 'all'),
    ]
    # ========================= CHOICES END

    # ========================= NATURAL KEY
    tour = models.ForeignKey(Tour, related_name='+', on_delete=models.PROTECT)
    aircraft = models.ForeignKey(Object, related_name='+', on_delete=models.PROTECT)
    filter_type = models.CharField(max_length=16, choices=filter_choices, default=NO_FILTER, db_index=True)
    player = models.ForeignKey(Player, related_name='+', on_delete=models.PROTECT, null=True)
    # ========================= NATURAL KEY END

    # ========================= SORTABLE FIELDS
    total_flight_time = models.BigIntegerField(default=0, db_index=True)
    khr = models.FloatField(default=0, db_index=True)
    gkhr = models.FloatField(default=0, db_index=True)
    kd = models.FloatField(default=0, db_index=True)
    gkd = models.FloatField(default=0, db_index=True)
    accuracy = models.FloatField(default=0, db_index=True)
    bomb_rocket_accuracy = models.FloatField(default=0, db_index=True)
    plane_survivability = models.FloatField(default=0, db_index=True)
    pilot_survivability = models.FloatField(default=0, db_index=True)
    plane_lethality = models.FloatField(default=0, db_index=True)
    pilot_lethality = models.FloatField(default=0, db_index=True)
    elo = models.IntegerField(default=1500, db_index=True)
    rating = models.IntegerField(default=0, db_index=True)
    max_ak_streak = models.IntegerField(default=0, db_index=True)
    max_gk_streak = models.IntegerField(default=0, db_index=True)
    kills = models.BigIntegerField(default=0, db_index=True)
    ground_kills = models.BigIntegerField(default=0, db_index=True)
    # ========================= SORTABLE FIELDS END

    # ========================= NON-SORTABLE VISIBLE FIELDS
    plane_lethality_no_assists = models.FloatField(default=0)
    # TODO: At some point add pilot_lethality_no_assists.
    # Problem is, it can't be computed because it is not known how much of pilot_lethality_counter is assists.
    # Can't use pilot_lethality_counter - assists, since assists are defined for shotdowns.

    total_sorties = models.BigIntegerField(default=0)
    score = models.BigIntegerField(default=0)
    # Assists per hour
    ahr = models.FloatField(default=0)
    # Assists per death
    ahd = models.FloatField(default=0)

    assists = models.BigIntegerField(default=0)

    killboard_planes = JSONField(default=dict)
    killboard_ground = JSONField(default=dict)
    COALITIONS = (
        (Coalition.neutral, pgettext_lazy('coalition', _('neutral'))),
        (Coalition.coal_1, settings.COAL_1_NAME),
        (Coalition.coal_2, settings.COAL_2_NAME),
    )

    coalition = models.IntegerField(default=Coalition.neutral, choices=COALITIONS)

    aircraft_lost = models.BigIntegerField(default=0)
    deaths = models.BigIntegerField(default=0)
    captures = models.BigIntegerField(default=0)
    bailouts = models.BigIntegerField(default=0)
    ditches = models.BigIntegerField(default=0)
    landings = models.BigIntegerField(default=0)
    in_flight = models.BigIntegerField(default=0)
    crashes = models.BigIntegerField(default=0)
    shotdown = models.BigIntegerField(default=0)

    deaths_to_accident = models.BigIntegerField(default=0)
    deaths_to_aa = models.BigIntegerField(default=0)
    aircraft_lost_to_accident = models.BigIntegerField(default=0)
    aircraft_lost_to_aa = models.BigIntegerField(default=0)

    max_score_streak = models.IntegerField(default=0, db_index=True)
    max_ak_streak_player = models.ForeignKey(Player, related_name='+', on_delete=models.PROTECT, null=True)
    max_gk_streak_player = models.ForeignKey(Player, related_name='+', on_delete=models.PROTECT, null=True)
    max_score_streak_player = models.ForeignKey(Player, related_name='+', on_delete=models.PROTECT, null=True)

    # These following 3 are for player buckets only.
    # TODO: Make sure this does not conflict with a retro compute.
    current_score_streak = models.IntegerField(default=0)
    current_ak_streak = models.IntegerField(default=0)
    current_gk_streak = models.IntegerField(default=0)

    best_score_in_sortie = models.IntegerField(default=0)
    best_score_sortie = models.ForeignKey(Sortie, related_name='+', on_delete=models.PROTECT, null=True)
    best_ak_in_sortie = models.IntegerField(default=0)
    best_ak_sortie = models.ForeignKey(Sortie, related_name='+', on_delete=models.PROTECT, null=True)
    best_gk_in_sortie = models.IntegerField(default=0)
    best_gk_sortie = models.ForeignKey(Sortie, related_name='+', on_delete=models.PROTECT, null=True)

    ammo_breakdown = JSONField(default=default_ammo_breakdown)
    # ========================== NON-SORTABLE VISIBLE FIELDS END

    # ========================== NON-VISIBLE HELPER FIELDS (used to calculate other visible fields)
    ammo_shot = models.BigIntegerField(default=0)
    ammo_hit = models.BigIntegerField(default=0)

    bomb_rocket_shot = models.BigIntegerField(default=0)
    bomb_rocket_hit = models.BigIntegerField(default=0)

    sorties_plane_was_hit = models.BigIntegerField(default=0)
    plane_survivability_counter = models.BigIntegerField(default=0)
    pilot_survivability_counter = models.BigIntegerField(default=0)
    plane_lethality_counter = models.BigIntegerField(default=0)  # = Air kills + Assists.
    pilot_lethality_counter = models.BigIntegerField(default=0)  # = Pilot kills + Asissts on a pilot kill.
    distinct_enemies_hit = models.BigIntegerField(default=0)
    pilot_kills = models.BigIntegerField(default=0)

    has_juiced_variant = models.BooleanField(default=False, db_index=True)
    has_bomb_variant = models.BooleanField(default=False, db_index=True)

    # This is to check if we reset accident/aa stats. There was a bugged version which doubled this.
    reset_accident_aa_stats = models.BooleanField(default=False, db_index=True)
    # Dito for Elo computations, this was bugged.
    reset_elo = models.BooleanField(default=False, db_index=True)
    # Ammo breakdowns recomputation to include more data.
    reset_ammo_breakdown = models.BooleanField(default=False, db_index=True)
    reset_ammo_breakdown_2 = models.BooleanField(default=False, db_index=True)
    # ========================== NON-VISIBLE HELPER FIELDS  END

    class Meta:
        # The long table name is to avoid any conflicts with new tables defined in the main branch of IL2 Stats.
        db_table = "AircraftBucket_MOD_STATS_BY_AIRCRAFT"
        ordering = ['-id']

    def update_derived_fields(self):
        ai_kills = 0
        if 'aircraft_light' in self.killboard_ground:
            ai_kills += self.killboard_ground['aircraft_light']
        if 'aircraft_medium' in self.killboard_ground:
            ai_kills += self.killboard_ground['aircraft_medium']
        if 'aircraft_heavy' in self.killboard_ground:
            ai_kills += self.killboard_ground['aircraft_heavy']

        self.khr = compute_float(self.kills, self.flight_time_hours)
        self.gkhr = compute_float(self.ground_kills, self.flight_time_hours)
        self.kd = compute_float(self.kills, self.relive)
        self.gkd = compute_float(self.ground_kills, self.relive)
        self.accuracy = compute_float(self.ammo_hit * 100, self.ammo_shot, 1)
        self.bomb_rocket_accuracy = compute_float(self.bomb_rocket_hit * 100, self.bomb_rocket_shot, 1)
        self.plane_survivability = compute_float(100 * self.plane_survivability_counter, self.sorties_plane_was_hit)
        self.pilot_survivability = compute_float(100 * self.pilot_survivability_counter, self.sorties_plane_was_hit)
        self.plane_lethality = compute_float(100 * self.plane_lethality_counter, self.distinct_enemies_hit)
        self.pilot_lethality = compute_float(100 * self.pilot_lethality_counter, self.distinct_enemies_hit)
        self.plane_lethality_no_assists = compute_float(100 * (self.kills - ai_kills), self.distinct_enemies_hit)
        self.update_rating()
        self.ahr = compute_float(self.assists, self.flight_time_hours)
        self.ahd = compute_float(self.assists, self.relive)
        self.has_juiced_variant = has_juiced_variant(self.aircraft)
        self.has_bomb_variant = has_bomb_variant(self.aircraft)

        # If the bucket is being saved like this, then the bucket was already either reset,
        # or it was made after the bug was fixed.
        self.reset_accident_aa_stats = True
        self.reset_elo = True
        self.reset_ammo_breakdown = True
        self.reset_ammo_breakdown_2 = True

    def update_rating(self):
        if self.player is None:
            # score per death
            sd = self.score / max(self.relive, 1)
            # score per hour
            shr = self.score / max(self.flight_time_hours, 1)
            self.rating = int(sd * shr)
            # Note this rating is NOT multiplied by score
            # In the original formula, you got higher rating the longer you played with the same performance.
            # This was due to the multiplication by score. This is not wanted for global aircraft stats.
            # Also no need to divide by 1000, since the nr tends to be small enouh to display as is.
        else:
            # score per death
            sd = self.score / max(self.relive, 1)
            # score per hour
            shr = self.score / max(self.flight_time_hours, 1)
            self.rating = (int((sd * shr * self.score) / 1000))

    @property
    def flight_time_hours(self):
        return self.total_flight_time / 3600

    @property
    def relive(self):
        return self.deaths + self.captures

    @property
    def rating_format(self):
        return rating_format_helper(self.rating)

    # TODO: Refactor the following 4 methods, DRY
    def percent_pvp_helper(self, key):
        if key in self.killboard_planes:
            percent = compute_float(self.killboard_planes[key] * 100, self.kills)
            total = self.killboard_planes[key]
            return percent_format(percent, total)
        else:
            return percent_format(0, 0)

    def percent_air_ai_helper(self, key):
        if key in self.killboard_ground:
            percent = compute_float(self.killboard_ground[key] * 100, self.kills)
            total = self.killboard_ground[key]
            return percent_format(percent, total)
        else:
            return percent_format(0, 0)

    def percent_ground_helper(self, key):
        if key in self.killboard_ground:
            percent = compute_float(self.killboard_ground[key] * 100, self.ground_kills)
            total = self.killboard_ground[key]
            return percent_format(percent, total)
        else:
            return percent_format(0, 0)

    def percent_player_ground_helper(self, key):
        if key in self.killboard_planes:
            percent = compute_float(self.killboard_planes[key] * 100, self.ground_kills)
            total = self.killboard_planes[key]
            return percent_format(percent, total)
        else:
            return percent_format(0, 0)

    @property
    def percent_light_kills(self):
        return self.percent_pvp_helper('aircraft_light')

    @property
    def percent_medium_kills(self):
        return self.percent_pvp_helper('aircraft_medium')

    @property
    def percent_heavy_kills(self):
        return self.percent_pvp_helper('aircraft_heavy')

    @property
    def percent_transport_kills(self):
        return self.percent_pvp_helper('aircraft_transport')

    @property
    def percent_light_ai_kills(self):
        return self.percent_air_ai_helper('aircraft_light')

    @property
    def percent_medium_ai_kills(self):
        return self.percent_air_ai_helper('aircraft_medium')

    @property
    def percent_heavy_ai_kills(self):
        return self.percent_air_ai_helper('aircraft_heavy')

    @property
    def percent_transport_ai_kills(self):
        return self.percent_air_ai_helper('aircraft_transport')

    @property
    def percent_player_tank_heavy(self):
        return self.percent_player_ground_helper('tank_heavy')

    @property
    def percent_player_tank_medium(self):
        return self.percent_player_ground_helper('tank_medium')

    @property
    def percent_player_tank_light(self):
        return self.percent_player_ground_helper('tank_light')

    @property
    def percent_player_truck(self):
        return self.percent_player_ground_helper('truck')

    @property
    def percent_tank_heavy(self):
        return self.percent_ground_helper('tank_heavy')

    @property
    def percent_tank_medium(self):
        return self.percent_ground_helper('tank_medium')

    @property
    def percent_tank_light(self):
        return self.percent_ground_helper('tank_light')

    @property
    def percent_armoured_vehicle(self):
        return self.percent_ground_helper('armoured_vehicle')

    @property
    def percent_car(self):
        return self.percent_ground_helper('car')

    @property
    def percent_truck(self):
        return self.percent_ground_helper('truck')

    @property
    def percent_aaa_heavy(self):
        return self.percent_ground_helper('aaa_heavy')

    @property
    def percent_aaa_light(self):
        return self.percent_ground_helper('aaa_light')

    @property
    def percent_aaa_mg(self):
        return self.percent_ground_helper('aaa_mg')

    @property
    def percent_machine_gunner(self):
        return self.percent_ground_helper('machine_gunner')

    @property
    def percent_aerostat(self):
        return self.percent_ground_helper('aerostat')

    @property
    def percent_searchlight(self):
        return self.percent_ground_helper('searchlight')

    @property
    def percent_locomotive(self):
        return self.percent_ground_helper('locomotive')

    @property
    def percent_wagon(self):
        return self.percent_ground_helper('wagon')

    @property
    def percent_artillery_field(self):
        return self.percent_ground_helper('artillery_field')

    @property
    def percent_artillery_howitzer(self):
        return self.percent_ground_helper('artillery_howitzer')

    @property
    def percent_artillery_rocket(self):
        return self.percent_ground_helper('artillery_rocket')

    @property
    def percent_ship(self):
        return self.percent_ground_helper('ship')

    @property
    def percent_ship_heavy(self):
        return self.percent_ground_helper('ship_heavy')

    @property
    def percent_ship_medium(self):
        return self.percent_ground_helper('ship_medium')

    @property
    def percent_ship_light(self):
        return self.percent_ground_helper('ship_light')

    @property
    def percent_aircraft_static(self):
        return self.percent_ground_helper('aircraft_static')

    @property
    def percent_vehicle_static(self):
        return self.percent_ground_helper('vehicle_static')

    @property
    def percent_airfield(self):
        return self.percent_ground_helper('airfield')

    @property
    def percent_bridge(self):
        return self.percent_ground_helper('bridge')

    @property
    def percent_industrial(self):
        return self.percent_ground_helper('industrial')

    @property
    def percent_building_big(self):
        return self.percent_ground_helper('building_big')

    @property
    def percent_building_medium(self):
        return self.percent_ground_helper('building_medium')

    @property
    def percent_building_small(self):
        return self.percent_ground_helper('building_small')

    def percent_of_sorties_helper(self, occurrences):
        percent = compute_float(occurrences * 100, self.total_sorties)
        total = occurrences
        return percent_format(percent, total)

    @property
    def percent_deaths(self):
        return self.percent_of_sorties_helper(self.deaths)

    @property
    def percent_bailouts(self):
        return self.percent_of_sorties_helper(self.bailouts)

    @property
    def percent_captures(self):
        return self.percent_of_sorties_helper(self.captures)

    @property
    def percent_ditches(self):
        return self.percent_of_sorties_helper(self.ditches)

    @property
    def percent_landings(self):
        return self.percent_of_sorties_helper(self.landings)

    @property
    def percent_in_flight(self):
        return self.percent_of_sorties_helper(self.in_flight)

    @property
    def percent_crashes(self):
        return self.percent_of_sorties_helper(self.crashes)

    @property
    def percent_shotdown(self):
        return self.percent_of_sorties_helper(self.shotdown)

    @property
    def percent_aircraft_lost(self):
        return self.percent_of_sorties_helper(self.aircraft_lost)

    @property
    def kills_per_loss(self):
        return compute_float(self.kills, self.aircraft_lost)

    @property
    def kills_per_sortie(self):
        return compute_float(self.kills, self.total_sorties)

    @property
    def ground_kills_per_loss(self):
        return compute_float(self.ground_kills, self.aircraft_lost)

    @property
    def ground_kills_per_sortie(self):
        return compute_float(self.ground_kills, self.total_sorties)

    @property
    def percent_deaths_to_accidents(self):
        percent = compute_float(100 * self.deaths_to_accident, self.relive)
        total = self.deaths_to_accident
        return percent_format(percent, total)

    @property
    def percent_deaths_to_aa(self):
        percent = compute_float(100 * self.deaths_to_aa, self.relive)
        total = self.deaths_to_aa
        return percent_format(percent, total)

    @property
    def percent_aircraft_lost_to_accidents(self):
        percent = compute_float(100 * self.aircraft_lost_to_accident, self.aircraft_lost)
        total = self.aircraft_lost_to_accident
        return percent_format(percent, total)

    @property
    def percent_aircraft_lost_to_aa(self):
        percent = compute_float(100 * self.aircraft_lost_to_aa, self.aircraft_lost)
        total = self.aircraft_lost_to_aa
        return percent_format(percent, total)

    def get_aircraft_url(self):
        return get_aircraft_url(self.aircraft.id, self.tour.id, self.NO_FILTER, self.player)

    def get_url_no_mods(self):
        return get_aircraft_url(self.aircraft.id, self.tour.id, self.NO_BOMBS_NO_JUICE, self.player)

    def get_url_bombs(self):
        return get_aircraft_url(self.aircraft.id, self.tour.id, self.BOMBS, self.player)

    def get_url_juiced(self):
        return get_aircraft_url(self.aircraft.id, self.tour.id, self.JUICED, self.player)

    def get_url_all_mods(self):
        return get_aircraft_url(self.aircraft.id, self.tour.id, self.ALL, self.player)

    def get_killboard_url(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.player, self.NO_FILTER)

    def get_killboard_no_mods(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.player, self.NO_BOMBS_NO_JUICE)

    def get_killboard_bombs(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.player, self.BOMBS)

    def get_killboard_juiced(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.player, self.JUICED)

    def get_killboard_all_mods(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.player, self.ALL)

    def get_killboard_enemy_no_filter(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.player, self.filter_type, self.NO_FILTER)

    def get_killboard_enemy_no_mods(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.player, self.filter_type, self.NO_BOMBS_NO_JUICE)

    def get_killboard_enemy_bombs(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.player, self.filter_type, self.BOMBS)

    def get_killboard_enemy_juiced(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.player, self.filter_type, self.JUICED)

    def get_killboard_enemy_all_mods(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.player, self.filter_type, self.ALL)

    def get_aircraft_pilot_rankings_url(self):
        return get_aircraft_pilot_rankings_url(self.aircraft.id, self.tour.id, self.filter_type)

    def get_pilot_url(self):
        return get_aircraft_url(self.aircraft.id, self.tour.id, self.NO_FILTER, self.player)

    def get_pilot_filtered_url(self):
        return get_aircraft_url(self.aircraft.id, self.tour.id, str(self.filter_type), self.player)

    def increment_ammo_received(self, ammo_dict, pilot_snipe):
        self.__increment_helper(ammo_dict, self.ammo_breakdown[RECEIVED], pilot_snipe)

    def increment_ammo_given(self, ammo_dict, pilot_snipe):
        self.__increment_helper(ammo_dict, self.ammo_breakdown[GIVEN], pilot_snipe)

    @staticmethod
    def __increment_helper(ammo_dict, sub_dict, pilot_snipe):
        # TODO: Refactor this mess if possible.
        #       Perhaps create data classes that we later convert automagically into dicts/jsons for storage?
        #       Or adapt the database schema to not use JSON.
        key = multi_key_to_string(list(ammo_dict.keys()))
        if not key:
            return

        if key not in sub_dict[TOTALS]:
            sub_dict[TOTALS][key] = {
                INST: 0,
                COUNT: dict(),
                M2: dict(),
                STANDARD_DEVIATION: dict(),
                PILOT_KILLS: 0,
                SAMPLE: None,
                RESERVOIR_COUNTER: 0
            }
            sub_dict[AVERAGES][key] = dict()
            for ammo_key in ammo_dict:
                sub_dict[TOTALS][key][COUNT][ammo_key] = 0

        update_reservoir(ammo_dict, sub_dict[TOTALS][key])
        sub_dict[TOTALS][key][INST] += 1
        sub_dict[TOTALS][key][PILOT_KILLS] += 1 if pilot_snipe else 0
        for ammo_key in ammo_dict:
            times_hit = ammo_dict[ammo_key]
            sub_dict[TOTALS][key][COUNT][ammo_key] += times_hit
            mean_delta = times_hit
            if ammo_key in sub_dict[AVERAGES][key]:
                mean_delta -= sub_dict[AVERAGES][key][ammo_key]
            new_mean = compute_float(
                sub_dict[TOTALS][key][COUNT][ammo_key],
                sub_dict[TOTALS][key][INST]
            )
            sub_dict[AVERAGES][key][ammo_key] = new_mean

            # Welford's online algorithm to compute variance in one pass.
            if ammo_key not in sub_dict[TOTALS][key][M2]:
                sub_dict[TOTALS][key][M2][ammo_key] = 0

            m2_delta = times_hit - new_mean
            sub_dict[TOTALS][key][M2][ammo_key] += m2_delta * mean_delta
            if sub_dict[TOTALS][key][INST] > 1:
                sub_dict[TOTALS][key][STANDARD_DEVIATION][ammo_key] = round(math.sqrt(
                    sub_dict[TOTALS][key][M2][ammo_key] / (sub_dict[TOTALS][key][INST] - 1),
                ), 2)


def multi_key_to_string(keys, separator='|'):
    keys = sorted(keys)
    if len(keys) == 0:
        return ''
    if len(keys) == 1:
        return str(keys[0])

    result = str(keys[0])
    for key in keys[1:]:
        result += separator + str(key)
    return result


def string_to_multikey(string, separator='|'):
    return string.split(separator)


def get_aircraft_url(aircraft_id, tour_id, bucket_filter='NO_FILTER', player=None):
    if player is None:
        url = '{url}?tour={tour_id}'.format(url=reverse('stats:aircraft', args=[aircraft_id, bucket_filter]),
                                            tour_id=tour_id)
    else:
        url = '{url}?tour={tour_id}'.format(
            url=reverse('stats:pilot_aircraft',
                        args=[aircraft_id, bucket_filter, player.profile.id, player.nickname]),
            tour_id=tour_id)
    return url


def get_killboard_url(aircraft_id, tour_id, player, bucket_filter, enemy_filter='NO_FILTER'):
    if player is None:
        url = '{url}?tour={tour_id}&enemy_filter={enemy_filter}'.format(
            url=reverse('stats:aircraft_killboard', args=[aircraft_id, bucket_filter]),
            tour_id=tour_id, enemy_filter=enemy_filter)
    else:
        url = '{url}?tour={tour_id}&enemy_filter={enemy_filter}'.format(
            url=reverse('stats:pilot_aircraft_killboard',
                        args=[aircraft_id, bucket_filter, player.profile.id, player.nickname]),
            tour_id=tour_id, enemy_filter=enemy_filter)
    return url


def get_aircraft_pilot_rankings_url(aircraft_id, tour_id, bucket_filter):
    return '{url}?tour={tour_id}'.format(
        url=reverse('stats:aircraft_pilot_rankings', args=[aircraft_id, bucket_filter]),
        tour_id=tour_id)


# All pairs of aircraft. Here, aircraft_1.name < aircraft_2.name (Lex order)
class AircraftKillboard(models.Model):
    # ========================= NATURAL KEY
    aircraft_1 = models.ForeignKey(AircraftBucket, related_name='+', on_delete=models.PROTECT, db_index=True)
    aircraft_2 = models.ForeignKey(AircraftBucket, related_name='+', on_delete=models.PROTECT, db_index=True)
    tour = models.ForeignKey(Tour, related_name='+', on_delete=models.PROTECT, db_index=True)
    # ========================= NATURAL KEY END

    aircraft_1_kills = models.BigIntegerField(default=0)  # Nr times aircraft 1 hit aircraft 2 which lead to pilot death
    aircraft_1_shotdown = models.BigIntegerField(default=0)  # Nr times aircraft 1 shot down aircraft 2
    aircraft_1_assists = models.BigIntegerField(default=0)
    aircraft_1_pk_assists = models.BigIntegerField(default=0)
    aircraft_2_kills = models.BigIntegerField(default=0)  # Nr times aircraft 2 hit aircraft 1 which lead to pilot death
    aircraft_2_shotdown = models.BigIntegerField(default=0)  # Nr times aircraft 2 shot down aircraft 1
    aircraft_2_assists = models.BigIntegerField(default=0)
    aircraft_2_pk_assists = models.BigIntegerField(default=0)

    # These two count how many times aircraft_x hit aircraft_y at least once in a sortie.
    # To calculate survivability/lethality.
    aircraft_1_distinct_hits = models.BigIntegerField(default=0)
    aircraft_2_distinct_hits = models.BigIntegerField(default=0)

    # Helper fields in order to detect corrupted data.
    # This field is only relevant for killboards without Player
    reset_kills_turret_bug = models.BooleanField(default=False, db_index=True)
    # This field is only relevant for killboards with Player.
    reset_player_loses = models.BooleanField(default=False, db_index=True)

    class Meta:
        # The long table name is to avoid any conflicts with new tables defined in the main branch of IL2 Stats.
        db_table = "AircraftKillboard_MOD_STATS_BY_AIRCRAFT"
        ordering = ['-id']

    def get_aircraft_url(self, one_or_two):
        if one_or_two == 1:
            return get_aircraft_url(self.aircraft_1.aircraft.id, self.tour.id)
        else:
            return get_aircraft_url(self.aircraft_2.aircraft.id, self.tour.id)


# Additional fields to Sortie objects used by this mod.
class SortieAugmentation(models.Model):
    sortie = models.OneToOneField(Sortie, on_delete=models.PROTECT, primary_key=True,
                                  related_name='SortieAugmentation_MOD_STATS_BY_AIRCRAFT')
    sortie_stats_processed = models.BooleanField(default=False, db_index=True)
    player_stats_processed = models.BooleanField(default=False, db_index=True)
    fixed_aa_accident_stats = models.BooleanField(default=False, db_index=True)
    fixed_doubled_turret_killboards = models.BooleanField(default=False, db_index=True)
    added_player_kb_losses = models.BooleanField(default=False, db_index=True)
    computed_max_streaks = models.BooleanField(default=False, db_index=True)
    fixed_accuracy = models.BooleanField(default=False, db_index=True)
    recomputed_ammo_breakdown = models.BooleanField(default=False, db_index=True)
    recomputed_ammo_breakdown_2 = models.BooleanField(default=False, db_index=True)
    fixed_captures = models.BooleanField(default=False, db_index=True)


    class Meta:
        # The long table name is to avoid any conflicts with new tables defined in the main branch of IL2 Stats.
        db_table = "Sortie_MOD_STATS_BY_AIRCRAFT"

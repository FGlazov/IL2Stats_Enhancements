from django.db import models
from stats.models import Tour, Object, Sortie, rating_format_helper
from mission_report.constants import Coalition
from django.contrib.postgres.fields import JSONField
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.conf import settings
from django.urls import reverse


def compute_float(numerator, denominator, round_to=2):
    return round(numerator / max(denominator, 1), round_to)


def has_juiced_variant(aircraft):
    juiceables = ['P-47D-28', 'P-47D-22', 'P-51D-15', 'La-5 (series 8)', 'Bf 109 G-6 Late', 'Bf 109 K-4',
                  'Spitfire Mk.IXe', 'Hurricane Mk.II', 'Tempest Mk.V ser.2']

    return aircraft.name in juiceables


def has_bomb_variant(aircraft):
    if aircraft.name == "P-38J-25" or aircraft.name == "Me 262 A":
        return True

    if aircraft.cls != "aircraft_light":
        return False

    no_jabo_possible = ['Spitfire Mk.VB', 'Yak-9 ser.1', 'Yak-9T ser.1', 'Hurricane Mk.II']
    if aircraft.name in no_jabo_possible:
        return False

    return True


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
    filter_type = models.CharField(max_length=16, choices=filter_choices, default=NO_FILTER)
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
    # ========================= SORTABLE FIELDS END

    # ========================= NON-SORTABLE VISIBLE FIELDS
    total_sorties = models.BigIntegerField(default=0)
    score = models.BigIntegerField(default=0)
    # Assists per hour
    ahr = models.FloatField(default=0)
    # Assists per death
    ahd = models.FloatField(default=0)

    kills = models.BigIntegerField(default=0)
    ground_kills = models.BigIntegerField(default=0)
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

    # ========================== NON-VISIBLE HELPER FIELDS  END

    class Meta:
        # The long table name is to avoid any conflicts with new tables defined in the main branch of IL2 Stats.
        db_table = "AircraftBucket_MOD_STATS_BY_AIRCRAFT"
        ordering = ['-id']

    def update_derived_fields(self):
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
        self.update_rating()
        self.ahr = compute_float(self.assists, self.flight_time_hours)
        self.ahd = compute_float(self.assists, self.relive)
        self.has_juiced_variant = has_juiced_variant(self.aircraft)
        self.has_bomb_variant = has_bomb_variant(self.aircraft)

    def update_rating(self):
        # score per death
        sd = self.score / max(self.relive, 1)
        # score per hour
        shr = self.score / max(self.flight_time_hours, 1)
        self.rating = int(sd * shr)
        # Note this rating is NOT multiplied by score
        # In the original formula, you got higher rating the longer you played with the same performance.
        # This was due to the multiplication by score. This is not wanted for aircraft stats.
        # Also no need to divide by 1000, since the nr tends to be small enouh to display as is.

    @property
    def flight_time_hours(self):
        return self.total_flight_time / 3600

    @property
    def relive(self):
        return self.deaths + self.captures

    @property
    def rating_format(self):
        return rating_format_helper(self.rating)

    def percent_pvp_helper(self, key):
        if key in self.killboard_planes:
            return str(compute_float(self.killboard_planes[key] * 100, self.kills)) + '%'
        else:
            return '0%'

    def percent_air_ai_helper(self, key):
        if key in self.killboard_ground:
            return str(compute_float(self.killboard_ground[key] * 100, self.kills)) + '%'
        else:
            return '0%'

    def percent_ground_helper(self, key):
        if key in self.killboard_ground:
            return str(compute_float(self.killboard_ground[key] * 100, self.ground_kills)) + '%'
        else:
            return '0%'

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
        return str(compute_float(occurrences * 100, self.total_sorties)) + "%"

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

    def get_aircraft_url(self):
        return get_aircraft_url(self.aircraft.id, self.tour.id, self.NO_FILTER)

    def get_url_no_mods(self):
        return get_aircraft_url(self.aircraft.id, self.tour.id, self.NO_BOMBS_NO_JUICE)

    def get_url_bombs(self):
        return get_aircraft_url(self.aircraft.id, self.tour.id, self.BOMBS)

    def get_url_juiced(self):
        return get_aircraft_url(self.aircraft.id, self.tour.id, self.JUICED)

    def get_url_all_mods(self):
        return get_aircraft_url(self.aircraft.id, self.tour.id, self.ALL)

    def get_killboard_url(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.NO_FILTER)

    def get_killboard_no_mods(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.NO_BOMBS_NO_JUICE)

    def get_killboard_bombs(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.BOMBS)

    def get_killboard_juiced(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.JUICED)

    def get_killboard_all_mods(self):
        return get_killboard_url(self.aircraft.id, self.tour.id, self.ALL)


def get_aircraft_url(aircraft_id, tour_id, bucket_filter='NO_FILTER'):
    url = '{url}?tour={tour_id}'.format(url=reverse('stats:aircraft', args=[aircraft_id, bucket_filter]),
                                        tour_id=tour_id)
    return url


def get_killboard_url(aircraft_id, tour_id, bucket_filter):
    url = '{url}?tour={tour_id}'.format(url=reverse('stats:aircraft_killboard', args=[aircraft_id, bucket_filter]),
                                        tour_id=tour_id)
    return url


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

    class Meta:
        # The long table name is to avoid any conflicts with new tables defined in the main branch of IL2 Stats.
        db_table = "Sortie_MOD_STATS_BY_AIRCRAFT"

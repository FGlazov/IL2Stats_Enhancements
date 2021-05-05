from .background_job import BackgroundJob
from stats.models import Sortie
from ..aircraft_mod_models import AircraftBucket, AircraftKillboard


class FixTurretKillboards(BackgroundJob):
    """
    A bug in the early versions of 1.2.X the to double kills by aircraft turrets in killboards without Player.
    This also affected Elo calculations and plane/pilot lethality.

    This job resets all the killoboards, Elos and lethalities,, and recomputes them.
    """

    def reset_relevant_fields(self):
        AircraftBucket.objects.filter(player=None, reset_elo=False).update(
            elo=1500,
            pilot_kills=0,
            distinct_enemies_hit=0,
            plane_lethality_counter=0,
            pilot_lethality_counter=0,
            reset_elo=True)
        AircraftKillboard.objects.filter(
            aircraft_1__player=None,
            aircraft_2__player=None,
            reset_kills_turret_bug=False).delete()

    def query_find_sorties(self, tour_cutoff):
        return (Sortie.objects.filter(SortieAugmentation_MOD_STATS_BY_AIRCRAFT__fixed_doubled_turret_killboards=False,
                                      aircraft__cls_base='aircraft', tour__id__gte=tour_cutoff)
                .order_by('-tour__id', 'id'))

    def compute_for_sortie(self, sortie):
        from ..stats_whore import process_log_entries, get_sortie_type

        buckets = [(AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                         filter_type='NO_FILTER', player=None))[0]]
        filter_type = get_sortie_type(sortie)
        has_subtype = filter_type != 'NO_FILTER'
        if has_subtype:
            buckets.append((AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                                 filter_type=filter_type, player=None))[0])
        for bucket in buckets:
            process_log_entries(bucket, sortie, has_subtype, bucket.filter_type != 'NO_FILTER',
                                compute_only_pure_killboard_stats=True)

        sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.fixed_doubled_turret_killboards = True
        sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.save()

    def log_update(self, to_compute):
        return '[mod_stats_by_aircraft]: Fixing Elo and doubled killboard turret kills. {} sorties left to process.' \
            .format(to_compute)

    def log_done(self):
        return '[mod_stats_by_aircraft]: Completed fixing Elo and doubled killboard turret kills.'

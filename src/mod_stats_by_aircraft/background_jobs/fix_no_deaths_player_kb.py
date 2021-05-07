from .background_job import BackgroundJob
from stats.models import Sortie
from ..aircraft_mod_models import AircraftBucket, AircraftKillboard


class FixNoDeathsPlayerKB(BackgroundJob):
    """
    A bug in the early versions of 1.2.X the retroactive compute to not count player deaths in aircraft overview
    killboards.

    This job resets the loses, and recomputes them. Not that the reset is necessary, since the normal, not retroactive
    compute does not have this issue.
    """

    def reset_relevant_fields(self, tour_cutoff):
        AircraftKillboard.objects.filter(
            aircraft_1__player__isnull=False,
            reset_player_loses=False,
            tour__id__gte=tour_cutoff
        ).update(
            aircraft_2_kills=0,
            aircraft_2_shotdown=0,
            aircraft_2_assists=0,
            aircraft_2_pk_assists=0,
            aircraft_2_distinct_hits=0,
            reset_player_loses=True
        )

        AircraftKillboard.objects.filter(
            aircraft_2__player__isnull=False,
            reset_player_loses=False,
            tour__id__gte=tour_cutoff
        ).update(
            aircraft_1_kills=0,
            aircraft_1_shotdown=0,
            aircraft_1_assists=0,
            aircraft_1_pk_assists=0,
            aircraft_1_distinct_hits=0,
            reset_player_loses=True
        )

    def query_find_sorties(self, tour_cutoff):
        return (Sortie.objects.filter(SortieAugmentation_MOD_STATS_BY_AIRCRAFT__added_player_kb_losses=False,
                                      aircraft__cls_base='aircraft', tour__id__gte=tour_cutoff)
                .order_by('-tour__id'))

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
                                compute_only_pure_killboard_stats=True, stop_update_primary_bucket=True)

        sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.added_player_kb_losses = True
        sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.save()

    def log_update(self, to_compute):
        return '[mod_stats_by_aircraft]: Adding loses in player aircraft killboards {} sorties left to process.' \
            .format(to_compute)

    def log_done(self):
        return '[mod_stats_by_aircraft]: Completed adding loses in player aircraft killboards.'

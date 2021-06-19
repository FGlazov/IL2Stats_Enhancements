from .background_job import BackgroundJob
from stats.models import Sortie
from ..aircraft_mod_models import AircraftBucket
from ..aircraft_stats_compute import process_aircraft_stats, process_log_entries, get_sortie_type


class PlayerRetroCompute(BackgroundJob):
    """
    Aircraft stats by player were introduced in 1.2.0.

    If this mod is updated from 1.1.X or 1.0.X to some version above 1.2.0, this job makes sure that
    the missing stats by player are computed.

    The "AA/accident shotdown/deaths" fields were also introduced in 1.2.0, so this is computed as well.

    """

    def query_find_sorties(self, tour_cutoff):
        return (Sortie.objects.filter(SortieAugmentation_MOD_STATS_BY_AIRCRAFT__player_stats_processed=False,
                                      aircraft__cls_base='aircraft', tour__id__gte=tour_cutoff)
                .order_by('-tour__id', 'id'))

    def compute_for_sortie(self, sortie):
        process_aircraft_stats(sortie, sortie.player, is_retro_compute=True)

        bucket = (AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                       filter_type='NO_FILTER', player=None))[0]
        filter_type = get_sortie_type(sortie)
        has_subtype = filter_type != 'NO_FILTER'

        # To update killboards of buckets with Player shotdown in this sortie,
        # and also AA/accident shotdowns/deaths
        process_log_entries(bucket, sortie, has_subtype, False, stop_update_primary_bucket=True)
        bucket.save()

        if has_subtype:
            bucket = (AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                           filter_type=filter_type, player=None))[0]
            # To update killboards of buckets with Player shotdown in this sortie,
            # and also AA/accident shotdowns/deaths
            process_log_entries(bucket, sortie, True, True, stop_update_primary_bucket=True)
            bucket.save()

    def log_update(self, to_compute):
        return '[mod_stats_by_aircraft]: Retroactively computing player aircraft stats. {} sorties left to process.' \
            .format(to_compute)

    def log_done(self):
        return '[mod_stats_by_aircraft]: Completed retroactively computing player aircraft stats.'

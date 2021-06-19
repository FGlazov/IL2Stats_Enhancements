from .background_job import BackgroundJob
from stats.models import Sortie
from ..aircraft_mod_models import AircraftBucket
from ..aircraft_stats_compute import process_streaks_and_best_sorties, get_sortie_type


class StreaksRetroCompute(BackgroundJob):
    """
    Streaks in aircraft stats were introduced in 1.3.0

    This retroactively computes streaks when updating the mod.
    """

    def query_find_sorties(self, tour_cutoff):
        return (Sortie.objects.filter(SortieAugmentation_MOD_STATS_BY_AIRCRAFT__computed_max_streaks=False,
                                      aircraft__cls_base='aircraft', tour__id__gte=tour_cutoff)
                .order_by('-tour__id', 'id'))

    def compute_for_sortie(self, sortie):

        buckets = [(AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                         filter_type='NO_FILTER', player=sortie.player))[0]]
        filter_type = get_sortie_type(sortie)
        has_subtype = filter_type != 'NO_FILTER'
        if has_subtype:
            buckets.append((AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                                 filter_type=filter_type, player=sortie.player))[0])

        for bucket in buckets:
            process_streaks_and_best_sorties(bucket, sortie)
            bucket.update_derived_fields()
            bucket.save()

    def log_update(self, to_compute):
        return '[mod_stats_by_aircraft]: Retroactively computing aircraft streaks. {} sorties left to process.' \
            .format(to_compute)

    def log_done(self):
        return '[mod_stats_by_aircraft]: Completed retroactively computing aircraft streaks.'

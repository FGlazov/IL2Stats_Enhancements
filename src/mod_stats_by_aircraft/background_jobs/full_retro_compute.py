from .background_job import BackgroundJob
from stats.models import Sortie
from ..aircraft_stats_compute import process_aircraft_stats


class FullRetroCompute(BackgroundJob):
    """
    When the global aircraft stats mod is first installed, no aircraft stats have been computed yet.
    This job then is responsible for retroactively computing those aircraft stats by taking already
    stored Sortie objects.
    """

    def query_find_sorties(self, tour_cutoff):
        return (Sortie.objects.filter(SortieAugmentation_MOD_STATS_BY_AIRCRAFT__isnull=True,
                                      aircraft__cls_base='aircraft', tour__id__gte=tour_cutoff)
                .order_by('-tour__id', 'id'))

    def compute_for_sortie(self, sortie):
        process_aircraft_stats(sortie, is_retro_compute=True)
        process_aircraft_stats(sortie, sortie.player, is_retro_compute=True)

    def log_update(self, to_compute):
        return '[mod_stats_by_aircraft]: Retroactively computing aircraft stats. {} sorties left to process.' \
            .format(to_compute)

    def log_done(self):
        return '[mod_stats_by_aircraft]: Completed retroactively computing aircraft stats.'

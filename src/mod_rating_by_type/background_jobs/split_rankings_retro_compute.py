from django.db.models import Q

from .background_job import BackgroundJob
from stats.models import Sortie
from ..config_modules import module_active, MODULE_SPLIT_RANKINGS
from ..variant_utils import decide_adjusted_cls
from ..models import SortieAugmentation


class SplitRankingsRetroCompute(BackgroundJob):
    """
    Job responsible for retroactively computing SplitRankings. This is done when it is first activated.
    """

    def query_find_sorties(self, tour_cutoff):
        if not module_active(MODULE_SPLIT_RANKINGS):
            return Sortie.objects.none()

        return (Sortie.objects.filter(
            Q(SortieAugmentation_MOD_SPLIT_RANKINGS__computed_filtered_player=False) |
            Q(SortieAugmentation_MOD_SPLIT_RANKINGS=None),
            aircraft__cls_base='aircraft', tour__id__gte=tour_cutoff)
                .order_by('-tour__id', 'id'))

    def compute_for_sortie(self, sortie):
        from ..stats_whore import increment_subtype_persona

        cls = decide_adjusted_cls(sortie, touch_db=True, retroactive_compute=True)
        augmentation = SortieAugmentation.objects.get_or_create(
            sortie=sortie
        )[0]

        increment_subtype_persona(sortie, cls)

        augmentation.cls = cls
        augmentation.computed_filtered_player = True
        augmentation.save()

    def log_update(self, to_compute):
        return '[mod_rating_by_stats]: Retroactively computing split personas. {} sorties left to process.' \
            .format(to_compute)

    def log_done(self):
        return '[mod_rating_by_stats]: Completed retroactively computing split personas.'

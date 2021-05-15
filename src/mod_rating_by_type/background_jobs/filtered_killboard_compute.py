from django.db.models import Q, F

from .background_job import BackgroundJob
from stats.models import Sortie, LogEntry
from ..config_modules import module_active, MODULE_SPLIT_RANKINGS
from ..variant_utils import decide_adjusted_cls
from ..models import SortieAugmentation, FilteredPlayer, FilteredKillboard


class FilteredKillboardCompute(BackgroundJob):
    """
    Job responsible for computing killboards of FilteredPlayers.

    This is always done as a retroactive compute, since this requires looking at LogEntrys, which are saved at
    the end of a stats_whore run.

    Technically speaking, this could be done not-retroactively as well. The problem with this is that it would
    involve monkey patching the stats_whore function, which create compatbility issues with mod_stats_by_aircraft.

    """

    def __init__(self):
        super().__init__()
        self.unlimited_work = True

    def query_find_sorties(self, tour_cutoff):
        if not module_active(MODULE_SPLIT_RANKINGS):
            return Sortie.objects.none()

        return (Sortie.objects.filter(
            SortieAugmentation_MOD_SPLIT_RANKINGS__computed_filter_player_killboard=False,
            is_disco=False, aircraft__cls_base='aircraft', tour__id__gte=tour_cutoff)
                .order_by('-tour__id', 'id'))

    def compute_for_sortie(self, sortie):
        augmentation = SortieAugmentation.objects.get_or_create(
            sortie=sortie
        )[0]
        cls = augmentation.cls

        player = FilteredPlayer.objects.get_or_create(
            profile_id=sortie.player.profile.id,
            tour_id=sortie.tour.id,
            type='pilot',
            cls=cls,
        )[0]

        wins = LogEntry.objects.filter(
            act_sortie=sortie,
            cact_sortie__isnull=False,
            type='shotdown',
        ).exclude(
            act_sortie__coalition=F('cact_sortie__coalition')
        ).select_related('cact_sortie__player')

        losses = LogEntry.objects.filter(
            cact_sortie=sortie,
            act_sortie__isnull=False,
            type='shotdown',
        ).exclude(
            act_sortie__coalition=F('cact_sortie__coalition')
        ).select_related('act_sortie__player')

        for win in wins:
            killboard = FilteredKillboard.objects.get_or_create(
                player_1=player,
                player_2=win.cact_sortie.player
            )[0]

            killboard.won_1 += 1
            killboard.update_analytics()
            killboard.save()

        for loss in losses:
            killboard = FilteredKillboard.objects.get_or_create(
                player_1=player,
                player_2=loss.act_sortie.player
            )[0]

            killboard.won_2 += 1
            killboard.update_analytics()
            killboard.save()

        augmentation.computed_filter_player_killboard = True
        augmentation.save()

    def log_update(self, to_compute):
        return ''

    def log_done(self):
        return ''

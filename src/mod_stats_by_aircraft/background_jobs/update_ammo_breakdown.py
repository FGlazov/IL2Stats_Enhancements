from .background_job import BackgroundJob
from stats.models import Sortie
from ..aircraft_mod_models import AircraftBucket, default_ammo_breakdown
from ..aircraft_stats_compute import get_sortie_type, process_ammo_breakdown
from django.db.models import Q

from ..ammo_file_manager import reset_ammo_breakdown_csvs


class UpdateAmmoBreakdown(BackgroundJob):
    """
    Version 1.4.0 introduces more fields to ammo breakdowns, this job is responsible for retroactively computing
    those fields.
    """

    def reset_relevant_fields(self, tour_cutoff):
        updated = AircraftBucket.objects.filter(Q(reset_ammo_breakdown=False) | Q(reset_ammo_breakdown_2=False)).update(
            ammo_breakdown=default_ammo_breakdown(),
            reset_ammo_breakdown=True,
            reset_ammo_breakdown_2=True
        )

        if updated:
            reset_ammo_breakdown_csvs()

    def query_find_sorties(self, tour_cutoff):
        return (Sortie.objects.filter(Q(SortieAugmentation_MOD_STATS_BY_AIRCRAFT__recomputed_ammo_breakdown=False) |
                                      Q(SortieAugmentation_MOD_STATS_BY_AIRCRAFT__recomputed_ammo_breakdown_2=False),
                                      aircraft__cls_base='aircraft', tour__id__gte=tour_cutoff)
                .order_by('-tour__id'))

    def compute_for_sortie(self, sortie):
        if 'ammo_breakdown' in sortie.ammo:
            buckets = [(AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                             filter_type='NO_FILTER', player=None))[0],
                       (AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                             filter_type='NO_FILTER', player=sortie.player))[0]]
            filter_type = get_sortie_type(sortie)
            if filter_type != 'NO_FILTER':
                buckets.append((AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                                     filter_type=filter_type, player=None))[0])
                buckets.append((AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                                     filter_type=filter_type, player=sortie.player))[0])
            for bucket in buckets:
                process_ammo_breakdown(bucket, sortie, bucket.filter_type != 'NO_FILTER')
                bucket.save()

        sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.recomputed_ammo_breakdown = True
        sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.recomputed_ammo_breakdown_2 = True
        sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.save()
        pass

    def log_update(self, to_compute):
        return '[mod_stats_by_aircraft]: Updating ammo breakdowns. {} sorties left to process.' \
            .format(to_compute)

    def log_done(self):
        return '[mod_stats_by_aircraft]: Completed updating ammo breakdowns..'

from .background_job import BackgroundJob
from stats.models import Sortie
from ..aircraft_mod_models import AircraftBucket


class FixCorruptedAaAccidents(BackgroundJob):
    """
    A bug in the early versions of 1.2.X the retroactive compute to double accidental/aa deaths.

    This job resets the accidental/aa deaths, and recomputes them. Note that a simple halving would not work here,
    since missions processed after the bugged update did not double accidental/aa deaths.
    """

    def reset_relevant_fields(self):
        AircraftBucket.objects.filter(reset_accident_aa_stats=False).update(
            deaths_to_accident=0,
            deaths_to_aa=0,
            aircraft_lost_to_accident=0,
            aircraft_lost_to_aa=0,
            reset_accident_aa_stats=True
        )

    def query_find_sorties(self, tour_cutoff):
        return (Sortie.objects.filter(SortieAugmentation_MOD_STATS_BY_AIRCRAFT__fixed_aa_accident_stats=False,
                                      aircraft__cls_base='aircraft', tour__id__gte=tour_cutoff)
                .order_by('-tour__id'))

    def compute_for_sortie(self, sortie):
        from ..stats_whore import process_aa_accident_death, get_sortie_type

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
            process_aa_accident_death(bucket, sortie)
            bucket.update_derived_fields()
            bucket.save()

        sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.fixed_aa_accident_stats = True
        sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.save()

    def log_update(self, to_compute):
        return '[mod_stats_by_aircraft]: Fixing AA/Accidents aircraft lost/deaths stats. {} sorties left to process.' \
            .format(to_compute)

    def log_done(self):
        return '[mod_stats_by_aircraft]: Completed fixing AA/Accidents aircraft lost/deaths stats.'

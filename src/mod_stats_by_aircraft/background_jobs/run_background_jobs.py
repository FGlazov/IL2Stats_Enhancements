from django.db import transaction
from django.db.models import Max

from .full_retro_compute import FullRetroCompute
from .player_retro_compute import PlayerRetroCompute
from .fix_corrupted_aa_accident import FixCorruptedAaAccidents
from .fix_turret_killboards import FixTurretKillboards
from .fix_no_deaths_player_kb import FixNoDeathsPlayerKB
from stats.models import Tour
from stats.logger import logger
import config

# Subclasses of BackgroundJob, see background_job.py
jobs = [FullRetroCompute(), PlayerRetroCompute(), FixCorruptedAaAccidents(), FixTurretKillboards(),
        FixNoDeathsPlayerKB()]

LOG_COUNTER = 0
LOGGING_INTERVAL = 5  # How many batches are run before an update log is produced.
SORTIES_PER_BATCH = 1000  # How many sorties computed per batch

RETRO_COMPUTE_FOR_LAST_TOURS = config.get_conf()['stats'].getint('retro_compute_for_last_tours')
if RETRO_COMPUTE_FOR_LAST_TOURS is None:
    RETRO_COMPUTE_FOR_LAST_TOURS = 10


@transaction.atomic
def reset_corrupted_data():
    """
    Resets corrupted data created by bugs from earlier versions.

    Note this must be done before any new mission is processed, otherwise the new data would be overwritten
    if reset later after the mission is processed.
    """
    tour_cutoff = __get_tour_cutoff()
    if tour_cutoff is None:
        return

    for job in jobs:
        job.reset_relevant_fields(tour_cutoff)


@transaction.atomic
def run_background_jobs():
    """
    Responsible for running BackgroundJobs, which fill up missing data, and corrects broken data.

    @returns True if some work was done, False if there is no more work left to do.
    """

    tour_cutoff = __get_tour_cutoff()
    if tour_cutoff is None:
        return False

    for job in jobs:
        work_done = __run_background_job(job, tour_cutoff)
        if work_done:
            return True

    return False


def __run_background_job(job, tour_cutoff):
    global LOG_COUNTER

    backfill_sorties = job.query_find_sorties(tour_cutoff)
    nr_left = backfill_sorties.count()
    if nr_left == 0:
        return False

    if LOG_COUNTER == 0:
        logger.info(job.log_update(nr_left))
    LOG_COUNTER = (LOG_COUNTER + 1) % LOGGING_INTERVAL

    for sortie in backfill_sorties[0:SORTIES_PER_BATCH]:
        job.compute_for_sortie(sortie)

    if nr_left <= SORTIES_PER_BATCH:
        logger.info(job.log_done())
        LOG_COUNTER = 0

    return True


def __get_tour_cutoff():
    max_id = Tour.objects.aggregate(Max('id'))['id__max']
    if max_id is None:  # Edge case: No tour yet
        return None

    return max_id - RETRO_COMPUTE_FOR_LAST_TOURS

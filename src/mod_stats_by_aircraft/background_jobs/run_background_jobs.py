from django.db import transaction

from .background_job import get_tour_cutoff
from .full_retro_compute import FullRetroCompute
from .player_retro_compute import PlayerRetroCompute
from .streaks_retro_compute import StreaksRetroCompute
from .fix_corrupted_aa_accident import FixCorruptedAaAccidents
from .fix_turret_killboards import FixTurretKillboards
from .fix_no_deaths_player_kb import FixNoDeathsPlayerKB
from .fix_accuracy import FixAccuracy
from .update_ammo_breakdown import UpdateAmmoBreakdown
from stats.logger import logger

# Subclasses of BackgroundJob, see background_job.py
jobs = [FullRetroCompute(), PlayerRetroCompute(), StreaksRetroCompute(), FixCorruptedAaAccidents(),
        UpdateAmmoBreakdown(), FixTurretKillboards(), FixNoDeathsPlayerKB(), FixAccuracy()]

LOG_COUNTER = 0
LOGGING_INTERVAL = 5  # How many batches are run before an update log is produced.
SORTIES_PER_BATCH = 1000  # How many sorties computed per batch


@transaction.atomic
def reset_corrupted_data():
    """
    Resets corrupted data created by bugs from earlier versions.

    Note this must be done before any new mission is processed, otherwise the new data would be overwritten
    if reset later after the mission is processed.
    """
    tour_cutoff = get_tour_cutoff()
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

    tour_cutoff = get_tour_cutoff()
    if tour_cutoff is None:
        return False

    for job in jobs:
        work_done = __run_background_job(job, tour_cutoff)
        if work_done:
            return True

    return False


def __run_background_job(job, tour_cutoff):
    if not job.work_left and not job.unlimited_work:
        return False

    global LOG_COUNTER

    backfill_sorties = job.query_find_sorties(tour_cutoff)
    nr_left = backfill_sorties.count()
    if nr_left == 0:
        job.work_left = False
        return False

    if LOG_COUNTER == 0 and job.log_update(nr_left):
        logger.info(job.log_update(nr_left))
    LOG_COUNTER = (LOG_COUNTER + 1) % LOGGING_INTERVAL

    for sortie in backfill_sorties[0:SORTIES_PER_BATCH]:
        job.compute_for_sortie(sortie)

    if nr_left <= SORTIES_PER_BATCH:
        if job.log_done():
            logger.info(job.log_done())
        job.work_left = False
        LOG_COUNTER = 0

    return True


def retro_streak_compute_running():
    retro_streak_compute_jobs = [
        jobs[0],  # FullRetroCompute()
        jobs[1],  # PlayerRetroCompute()
        jobs[2],  # StreaksRetroCompute()
    ]
    return True in {job.work_left for job in retro_streak_compute_jobs}

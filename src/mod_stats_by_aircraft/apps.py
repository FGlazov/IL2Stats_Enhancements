from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

IGNORE_AI_KILLS_STREAKS = False

class ModConfig(AppConfig):
    name = 'mod_stats_by_aircraft'

    def ready(self):
        # frontend monkey patch
        from stats import urls as original_urls
        from . import urls as new_urls
        original_urls.urlpatterns = new_urls.urlpatterns

        # backend monkey patch
        from . import stats_whore
        from stats import stats_whore as old_stats_whore

        old_stats_whore.main = stats_whore.main
        old_stats_whore.stats_whore = stats_whore.stats_whore

        from . import models
        from stats import models as old_models
        old_models.Player.get_aircraft_overview_url = models.get_aircraft_overview_url

        try:
            from mod_rating_by_type.models import FilteredPlayer
            FilteredPlayer.get_aircraft_overview_url = models.get_aircraft_overview_url

            from mod_rating_by_type.background_jobs.run_background_jobs import jobs as rating_type_jobs
            from .background_jobs.run_background_jobs import jobs as aircraft_mod_jobs
            for rating_type_job in rating_type_jobs:
                aircraft_mod_jobs.append(rating_type_job)
        except RuntimeError:
            pass  # Case when mod_rating_by_type is not installed.


        # monkey-patch the new config parameter.
        import config

        config.DEFAULT['stats']['retro_compute_for_last_tours'] = 10

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


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

        # monkey-patch the new config parameter.
        import config

        config.DEFAULT['stats']['retro_compute_for_last_tours'] = 10
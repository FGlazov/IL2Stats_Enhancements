from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

from django.conf.urls import url


class ModConfig(AppConfig):
    name = 'mod_rating_by_type'

    def ready(self):
        # monkey-patch the new config parameter.
        import config
        config.DEFAULT['stats']['modules'] = ''
        from . import config_modules

        # Add ironman config middleware so pages know when to render "ironman rankings".
        import core.settings as settings
        settings.MIDDLEWARE.append('mod_rating_by_type.middleware.ironman_middleware')
        settings.MIDDLEWARE.append('mod_rating_by_type.middleware.aircraft_installed')

        # !!! monkey patch
        from stats import urls as original_urls
        from . import urls as new_urls
        original_urls.urlpatterns = new_urls.urlpatterns

        from stats import views as original_views
        from . import views as new_views
        original_views.pilot = new_views.pilot
        original_views.squad = new_views.squad
        original_views.squad_pilots = new_views.squad_pilots
        original_views.squad_rankings = new_views.squad_rankings
        original_views.pilot_rankings = new_views.pilot_rankings
        original_views.main = new_views.main
        original_views.tour = new_views.tour
        original_views.mission = new_views.mission
        original_views.pilot_sortie = new_views.pilot_sortie
        original_views.ironman_stats = new_views.ironman_stats
        original_views.pilot_vlife = new_views.pilot_vlife

        from . import report as new_report
        from mission_report.report import MissionReport, Object
        MissionReport.event_hit = new_report.event_hit
        MissionReport.event_damage = new_report.event_damage
        Object.got_damaged = new_report.got_damaged

        from stats import stats_whore as original_stats_whore
        from . import stats_whore as new_stats_whore
        original_stats_whore.create_new_sortie = new_stats_whore.create_new_sortie
        original_stats_whore.update_general = new_stats_whore.update_general
        original_stats_whore.update_bonus_score = new_stats_whore.update_bonus_score

        from stats.management.commands import import_csv_data as old_csv_data
        from . import import_csv_data as new_csv_data
        old_csv_data.Command.handle = new_csv_data.Command.handle

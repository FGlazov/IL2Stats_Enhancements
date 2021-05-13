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
        original_views.pilot_sortie_log = new_views.pilot_sortie_log
        original_views.pilot_sorties = new_views.pilot_sorties
        original_views.pilot_vlifes = new_views.pilot_vlifes
        original_views.pilot_awards = new_views.pilot_awards

        from . import report as new_report
        from mission_report.report import MissionReport, Object
        MissionReport.event_hit = new_report.event_hit
        Object.got_damaged = new_report.got_damaged
        Object.got_killed = new_report.got_killed
        Object.takeoff = new_report.takeoff

        from stats import stats_whore as original_stats_whore
        from . import stats_whore as new_stats_whore
        original_stats_whore.create_new_sortie = new_stats_whore.create_new_sortie
        original_stats_whore.update_general = new_stats_whore.update_general
        original_stats_whore.old_update_bonus_score = original_stats_whore.update_bonus_score
        original_stats_whore.update_bonus_score = new_stats_whore.update_bonus_score
        original_stats_whore.update_ammo = new_stats_whore.update_ammo
        original_stats_whore.update_sortie = new_stats_whore.update_sortie
        original_stats_whore.main = new_stats_whore.main

        from stats.management.commands import import_csv_data as old_csv_data
        from . import import_csv_data as new_csv_data
        old_csv_data.Command.handle = new_csv_data.Command.handle


        from stats.models import Player, Tour
        from . import models as new_models
        from .models import FilteredPlayer

        Tour.stats_summary_coal = new_models.stats_summary_coal

        Player.get_base_profile_url = FilteredPlayer.get_base_profile_url
        Player.get_light_profile_url = FilteredPlayer.get_light_profile_url
        Player.get_medium_profile_url = FilteredPlayer.get_medium_profile_url
        Player.get_heavy_profile_url = FilteredPlayer.get_heavy_profile_url

        Player.get_base_sorties_url = FilteredPlayer.get_base_sorties_url
        Player.get_light_sorties_url = FilteredPlayer.get_light_sorties_url
        Player.get_medium_sorties_url = FilteredPlayer.get_medium_sorties_url
        Player.get_heavy_sorties_url = FilteredPlayer.get_heavy_sorties_url

        Player.get_base_vlifes_url = FilteredPlayer.get_base_vlifes_url
        Player.get_light_vlifes_url = FilteredPlayer.get_light_vlifes_url
        Player.get_medium_vlifes_url = FilteredPlayer.get_medium_vlifes_url
        Player.get_heavy_vlifes_url = FilteredPlayer.get_heavy_vlifes_url

        Player.get_base_awards_url = FilteredPlayer.get_base_awards_url
        Player.get_light_awards_url = FilteredPlayer.get_light_awards_url
        Player.get_medium_awards_url = FilteredPlayer.get_medium_awards_url
        Player.get_heavy_awards_url = FilteredPlayer.get_heavy_awards_url

        Player.get_base_killboard_url = FilteredPlayer.get_base_killboard_url
        Player.get_light_killboard_url = FilteredPlayer.get_light_killboard_url
        Player.get_medium_killboard_url = FilteredPlayer.get_medium_killboard_url
        Player.get_heavy_killboard_url = FilteredPlayer.get_heavy_killboard_url

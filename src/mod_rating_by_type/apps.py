from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ModConfig(AppConfig):
    name = 'mod_rating_by_type'

    def ready(self):
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

        from . import report as new_report
        from mission_report.report import MissionReport

        MissionReport.event_hit = new_report.event_hit

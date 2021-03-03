from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ModConfig(AppConfig):
    name = 'mod_rating_by_type'

    def ready(self):
        # !!! monkey patch
        from stats import urls as original_urls
        from . import urls as new_urls
        original_urls.urlpatterns = new_urls.urlpatterns

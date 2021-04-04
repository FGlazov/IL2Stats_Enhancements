from .config_modules import MODULE_IRONMAN_STATS, module_active
from config import get_conf


# Inserts "Ironman Rankings" in navigation if the module is installed.
def ironman_middleware(get_response):
    # One-time configuration and initialization.

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        request.module_ironman = module_active(MODULE_IRONMAN_STATS)
        response = get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        return response

    return middleware


# Inserts "Aircraft Rankings" in navigation at top if the mod is installed.
# (The base.html inside that mod gets overwritten by the base.html inside this mod)
def aircraft_installed(get_response):
    # One-time configuration and initialization.

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        config = get_conf()

        request.aircraft_rankings_installed = False
        for mod in config['stats']['mods'].split(','):
            mod = mod.strip().lower()
            if mod == 'mod_stats_by_aircraft':
                request.aircraft_rankings_installed = True

        response = get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        return response

    return middleware

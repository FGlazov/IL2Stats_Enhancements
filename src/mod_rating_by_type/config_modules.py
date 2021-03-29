from config import get_conf

MODULE_SPLIT_RANKINGS = 'split_rankings'
MODULE_AMMO_BREAKDOWN = 'ammo_breakdown'
MODULE_IRONMAN_STATS = 'ironman_stats'
modules = {MODULE_SPLIT_RANKINGS, MODULE_AMMO_BREAKDOWN, MODULE_IRONMAN_STATS}


def get_active_modules():
    config = get_conf()
    result = set()

    for module in config['stats']['modules'].split(','):
        module = module.strip().lower()

        if not module:
            continue
        if module not in modules:
            print("[mod_rating_by_type] Unknown module " + module)
        else :
            print("[mod_rating_by_type] Added module " + module)
            result.add(module)

    if not result:
        print('[mod_rating_by_type] WARNING: No module selected. No modded content will be displayed!')

    return result


active_modules = get_active_modules()


# Expected is some MODULE_XXXXXXXXXXXX input, see global variables above.
def module_active(module):
    if module not in modules:
        print('[mod_rating_by_type] PROGRAMMING ERROR: Unknown module ' + str(module))

    return module in active_modules

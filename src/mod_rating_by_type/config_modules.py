from config import get_conf

MODULE_SPLIT_RANKINGS = 'split_rankings'
MODULE_AMMO_BREAKDOWN = 'ammo_breakdown'
MODULE_IRONMAN_STATS = 'ironman_stats'
MODULE_UNDAMAGED_BAILOUT_PENALTY = 'undamaged_bailout_penalty'
MODULE_FLIGHT_TIME_BONUS = 'flight_time_bonus'
MODULE_ADJUSTABLE_BONUSES_AND_PENALTIES = 'adjustable_bonuses_penalties'
MODULE_TOP_LAST_MISSION = 'top_last_mission'
MODULE_REARM_ACCURACY_WORKAROUND = 'rearm_accuracy_workaround'
MODULE_BAILOUT_ACCURACY_WORKAROUND = 'bailout_accuracy_workaround'
MODULE_MISSION_WIN_NEW_TOUR = 'mission_win_new_tour'
MODULE_AIR_STREAKS_NO_AI = 'air_streaks_no_ai'
MODULE_GUNNER_STATS = "gunner_stats"
modules = {MODULE_SPLIT_RANKINGS, MODULE_AMMO_BREAKDOWN, MODULE_IRONMAN_STATS, MODULE_UNDAMAGED_BAILOUT_PENALTY,
           MODULE_FLIGHT_TIME_BONUS, MODULE_ADJUSTABLE_BONUSES_AND_PENALTIES, MODULE_TOP_LAST_MISSION,
           MODULE_REARM_ACCURACY_WORKAROUND, MODULE_BAILOUT_ACCURACY_WORKAROUND, MODULE_MISSION_WIN_NEW_TOUR,
           MODULE_AIR_STREAKS_NO_AI, MODULE_GUNNER_STATS}


def get_active_modules():
    config = get_conf()
    result = set()

    for module in config['stats']['modules'].split(','):
        module = module.strip().lower()

        if not module:
            continue
        if module not in modules:
            print("[mod_rating_by_type] Unknown module " + module)
        else:
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

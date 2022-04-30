from .models import PlayerAugmentation
from stats.models import LogEntry

FIGHTER_WHITE_LIST = {'P-38J-25', 'Me 262 A'}
ATTACKER_WHITE_LIST = {'Ju 88 C-6'}
JABO_MODS = {'Ground attack modification', 'U17 strike modification'}
BOMBS_ROCKETS = ['FAB-100M', 'FAB-250tsk', 'GP ', 'MC ', 'SC ', 'SD ', '21cm WGr.42', 'lb Cooper', 'H.E.R.L.',
                 'Pz.Bl. 1', 'R-Sprgr. M8', 'P.u.W', 'ROS-82', 'RBS-82', 'ROFS-132', '50-T', '100-T', 'M64', 'M65',
                 'M8', 'FAB-250sv', 'FAB-500M', 'RP-3']


# The P-38 and Me-262 are considered as fighters for this function.
# (They're technically aircraft_medium, i.e. attackers)
def is_jabo(sortie):
    return True in [__is_modification_jabo(mod) for mod in sortie.modifications] or __payload_has_bomb(sortie.payload)


def __is_modification_jabo(mod):
    if 'bomb' in mod.lower() or 'rocket' in mod.lower():
        return True
    if mod in JABO_MODS:
        return True
    return False


def __payload_has_bomb(payload):
    for bomb_rocket in BOMBS_ROCKETS:
        if bomb_rocket in str(payload):
            return True
    return False


def decide_adjusted_cls(sortie, touch_db=False, retroactive_compute=False):
    """
    Every sortie needs a class for split rankings to work, i.e. is this a fighter, attacker, or bomber sortie. This
    comes from the fact that rating formula takes flight time, deaths, and score earned as an input. So, in order to
    properly pass flight time and deaths, sorties must get class.

    The naive way to decide class of a Sortie for split rankings would be to look at the class of the aircraft flown in
    that sortie. I.e. every sortie with a fighter plane would be counted towards fighter ranking, attacker plane sorties
    towards attacker rating etc.

    However, there are two edge casess where it makes sense to deviate from this. Namely:

    1. Jabo flights in fighter planes. Think of a P-47 or FW-190 which only took bombs/rockets.
       These jabo flights are counted towards attacker rating. Jabo flights are detected by looking at which
       modifcations the plane took.
    2. Attacker planes like BF 110, P-38, HS-129, IL-2s used as (heavy) fighters instead of attackers.
       This is decided by how many air kills were scored by the main guns of that plane.
    2a. If Air kills from main guns > ground kills, then it's counted towards figher rating,
        and the ground kills < air kills case is counted the other way around.
    2b. If it can't be decided like this (e.g. 0 air and ground kills), the system attempts to decide via the recent
        history of the player (i.e. did they recently take a lot of attackers out as ground pounders or heavy fighters?)
    2c. Fall back if that also doesn't work is to simply return "attacker".
    """
    player = sortie.player
    player_augmentation = PlayerAugmentation.objects.get_or_create(player=player)[0]
    if touch_db:
        player_augmentation.save()

    sortie_cls = sortie.aircraft.cls
    if sortie.aircraft.name_en in ATTACKER_WHITE_LIST:
        sortie_cls = 'medium'

    if sortie_cls == 'aircraft_heavy':
        return 'heavy'
    if sortie_cls not in ['aircraft_light', 'aircraft_medium']:
        return 'placeholder'

    # Was taken with bombs or rockets, so the intent was likely to ground pound.
    if is_jabo(sortie):
        return 'medium'

    # We have a fighter aircraft without any bombs/rockets, likely not used as a ground pounder.
    if sortie_cls == 'aircraft_light' or sortie.aircraft.name_en in FIGHTER_WHITE_LIST:
        return 'light'

    # We now have an attacker aircraft, which may have been used as a fighter or as an attacker.
    # Think of a BF-110, or an IL-2 in an early war scenario.
    # Here even with gunpods it's hard to tell a priori what the likely intent was, hence we try
    # and figure it out by how many air kills/ground kills the plane scored.
    if retroactive_compute:
        ak_from_guns = LogEntry.objects.filter(
            act_sortie=sortie,
            type='shotdown',
            cact_object__cls_base='aircraft'
        ).count()
    else:
        ak_from_guns = sortie.ak_total - sortie.turret_kills

    if ak_from_guns > sortie.gk_total:
        if touch_db:
            player_augmentation.increment_attacker_plane_as_fighter()
            player_augmentation.save()
        return 'light'
    elif sortie.gk_total > ak_from_guns:
        if touch_db:
            player_augmentation.increment_attacker_plane_as_attacker()
            player_augmentation.save()
        return 'medium'

    # This case mostly happens if the plane died before scoring a victory.
    # Here we use the recent history of the player to decide.
    # E.g. if the player recently did a lot of attacker-as-fighter sorties, count it as 'light'.
    result = player_augmentation.decide_ambiguous_fighter_attacker_sortie()
    if result is None:
        return 'medium'
    return result

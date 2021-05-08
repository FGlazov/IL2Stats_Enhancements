from .models import PlayerAugmentation

FIGHTER_WHITE_LIST = {'P-38J-25', 'Me 262 A'}
JABO_MODS = {'Ground attack modification', 'U17 strike modification'}


# The P-38 and Me-262 are considered as fighters for this function.
# (They're technically aircraft_medium, i.e. attackers)
def is_jabo(sortie):
    return True in [__is_modification_jabo(mod) for mod in sortie.modifications]


def __is_modification_jabo(mod):
    if 'bomb' in mod.lower() or 'rocket' in mod.lower():
        return True
    if mod in JABO_MODS:
        return True
    return False


def decide_adjusted_cls(sortie, touch_db=False):
    player = sortie.player
    player_augmentation = PlayerAugmentation.objects.get_or_create(player=player)[0]
    if touch_db:
        player_augmentation.save()

    sortie_cls = sortie.aircraft.cls
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
    if sortie.ak_total + sortie.ak_assist > sortie.gk_total:
        if touch_db:
            player_augmentation.increment_attacker_plane_as_fighter()
            player_augmentation.save()
        return 'light'
    elif sortie.gk_total > sortie.ak_total + sortie.ak_assist:
        if touch_db:
            player_augmentation.increment_attacker_plane_as_attacker()
            player_augmentation.save()
        return 'medium'

    # This case mostly happens if the plane died before scoring a victory.
    # Here we use the recent history of the player to decide.
    # E.g. if the player recently did a lot of attacker-as-fighter sorties, count it as 'light'.
    result = player_augmentation.decide_ambiguous_fighter_attacker_sortie()
    if touch_db:
       print("AMBIG decision: ", result, sortie.ak_total+ sortie.ak_assist, sortie.gk_total)
    if result is None:
        return 'medium'
    return result

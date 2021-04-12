BOMB_VARIANT_WHITE_LIST = {'P-38J-25', 'Me 262 A', 'Bristol F2B (F.II)', 'Bristol F2B (F.III)', 'Halberstadt CL.II',
                           'Halberstadt CL.II 200hp'}
FIGHTER_WHITE_LIST = {'P-38J-25', 'Me 262 A'}
JABO_MODS = {'Ground attack modification', 'U17 strike modification'}


# The P-38 and Me-262 are considered as fighters for this function.
# (They're technically aircraft_medium, i.e. attackers)
def is_jabo(sortie):
    if sortie.aircraft.cls != 'aircraft_light' and sortie.aircraft.name_en not in BOMB_VARIANT_WHITE_LIST:
        return False

    for mod in sortie.modifications:
        if __is_modification_jabo(mod):
            return True

    return False


def __is_modification_jabo(mod):
    if 'bomb' in mod.lower() or 'rocket' in mod.lower():
        return True
    if mod in JABO_MODS:
        return True
    return False


def is_fighter(sortie):
    if is_jabo(sortie):
        return False
    return sortie.aircraft.cls == 'aircraft_light' or sortie.aircraft.name_en in FIGHTER_WHITE_LIST

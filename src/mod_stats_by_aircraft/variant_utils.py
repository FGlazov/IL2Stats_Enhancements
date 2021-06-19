BOMB_VARIANT_WHITE_LIST = {'P-38J-25', 'Me 262 A', 'Bristol F2B (F.II)', 'Bristol F2B (F.III)', 'Halberstadt CL.II',
                           'Halberstadt CL.II 200hp'}
BOMB_VARIANT_BLACK_LIST = {'Spitfire Mk.VB', 'Yak-9 series 1', 'Yak-9T series 1', 'Hurricane Mk.II', 'Albatros D.Va',
                           'Fokker D.VII', 'Fokker D.VIIF', 'Fokker Dr.I', 'Pfalz D.IIIa'}
JUICEABLES = {'P-47D-28', 'P-47D-22', 'P-51D-15', 'La-5 (series 8)', 'Bf 109 G-6 Late', 'Bf 109 K-4',
              'Spitfire Mk.IXe', 'Hurricane Mk.II', 'Tempest Mk.V ser.2', 'Spitfire Mk.XIV'}
#          P47/P51/Spit9/Spit14  Tempest                           BF-109 K-4          La-5
JUICES = {'150 grade fuel', 'Sabre IIA engine with +11 lb boost', 'DB 605 DC engine', 'M-82F engine',
          # Hurricane                          BF-109 G-6 Late
          'Merlin XX engine with +14 lb boost', 'MW-50 System'}
JABO_MODS = {'Ground attack modification', 'U17 strike modification'}


# Whether the aircraft has an upgraded engine or better fuel
def get_sortie_type(sortie):
    aircraft = sortie.aircraft
    if not has_juiced_variant(aircraft) and not has_bomb_variant(aircraft):
        return "NO_FILTER"

    if is_juiced(sortie):
        if is_jabo(sortie):
            return 'ALL'
        else:
            return 'JUICE'
    else:
        if is_jabo(sortie):
            return 'BOMBS'
        else:
            return 'NO_BOMBS_JUICE'


# The P-38 and Me-262 are considered as fighters for this function.
# (They're technically aircraft_medium, i.e. attackers)
def is_jabo(sortie):
    if sortie.aircraft.cls != 'aircraft_light' and sortie.aircraft.name_en not in BOMB_VARIANT_WHITE_LIST:
        return False

    for modification in sortie.modifications:
        if 'bomb' in modification.lower() or 'rocket' in modification.lower():
            return True
        if modification in JABO_MODS:
            return True

    return False


def is_juiced(sortie):
    if sortie.aircraft.name_en not in JUICEABLES:
        return False

    for modification in sortie.modifications:
        if modification in JUICES:
            return True

    return False


def has_bomb_variant(aircraft):
    if aircraft.name_en in BOMB_VARIANT_WHITE_LIST:
        return True

    if aircraft.cls != "aircraft_light" or aircraft.name_en in BOMB_VARIANT_BLACK_LIST:
        return False

    return True


def has_juiced_variant(aircraft):
    return aircraft.name_en in JUICEABLES

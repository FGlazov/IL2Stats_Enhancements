from stats.models import Object
from stats.logger import logger

TURRET_AMBIGUITIES = {
    'Bristol',
    'Halberstadt'
}

TURRET_TO_AIRCRAFT = {
    'turretbristolf2b_1': 'Bristol F2B (F.II)',
    'turretbristolf2bf2_1': 'Bristol F2B (F.II)',
    'turretbristolf2bf2_1_wm2': 'Bristol F2B (F.II)',
    'turretbristolf2bf2_1m': 'Bristol F2B (F.II)',
    'turretbristolf2bf3_1': 'Bristol F2B (F.III)',
    'turretbristolf2bf3_1_wm2': 'Bristol F2B (F.III)',
    'turretbristolf2bf3_1m': 'Bristol F2B (F.III)',
    'turrethalberstadtcl2_1': 'Halberstadt CL.II',
    'turrethalberstadtcl2_1_wm_beckap': 'Halberstadt CL.II',
    'turrethalberstadtcl2_1_wm_beckhe': 'Halberstadt CL.II',
    'turrethalberstadtcl2_1_wm_beckheap': 'Halberstadt CL.II',
    'turrethalberstadtcl2_1_wm_twinpar': 'Halberstadt CL.II',
    'turrethalberstadtcl2_1m': 'Halberstadt CL.II',
    'turrethalberstadtcl2_1m2': 'Halberstadt CL.II',
    'turrethalberstadtcl2au_1': 'Halberstadt CL.II 200hp',
    'turrethalberstadtcl2au_1_wm_beckap': 'Halberstadt CL.II 200hp',
    'turrethalberstadtcl2au_1_wm_beckhe': 'Halberstadt CL.II 200hp',
    'turrethalberstadtcl2au_1_wm_beckheap': 'Halberstadt CL.II 200hp',
    'turrethalberstadtcl2au_1_wm_twinpar': 'Halberstadt CL.II 200hp',
    'turrethalberstadtcl2au_1m': 'Halberstadt CL.II 200hp',
    'turrethalberstadtcl2au_1m2': 'Halberstadt CL.II 200hp',
}

TYPOS = {
    'Airco DH4': 'Airco D.H.4',
    'U-2VS': 'U-﻿2',
}


def turret_to_aircraft(turret):
    turret_name = turret.name_en
    log_name = turret.log_name

    aircraft_name = turret_name[:len(turret_name) - 7]
    if aircraft_name in TYPOS:
        aircraft_name = TYPOS[aircraft_name]
    if aircraft_name in TURRET_AMBIGUITIES:
        aircraft_name = TURRET_TO_AIRCRAFT[log_name]

    if 'B25' in aircraft_name:
        # It's an AI flight, which isn't (yet) supported.
        return None
    try:
        aircraft = Object.objects.filter(name_en=aircraft_name).get()
        return aircraft
    except Object.DoesNotExist:
        logger.warning("[mod_rating_by_type] Could not find aircraft for turret " + turret_name)
        return None

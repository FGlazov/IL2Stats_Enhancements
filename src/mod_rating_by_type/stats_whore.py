from collections import defaultdict
from django.conf import settings
from datetime import timedelta
from stats.models import Sortie

SORTIE_MIN_TIME = settings.SORTIE_MIN_TIME


def create_new_sortie(mission, profile, player, sortie, sortie_aircraft_id):
    sortie_tik_last = sortie.tik_bailout or sortie.tik_landed or sortie.tik_end or sortie.tik_last
    sortie_date_start = mission.date_start + timedelta(seconds=sortie.tik_spawn // 50)
    sortie_date_end = mission.date_start + timedelta(seconds=sortie_tik_last // 50)
    flight_time = round((sortie_tik_last - (sortie.tik_takeoff or sortie.tik_spawn)) / 50, 0)

    is_ignored = False
    # вылет игнорируется если общее время вылета меньше установленного конфигом
    if SORTIE_MIN_TIME:
        if (sortie_tik_last // 50) - (sortie.tik_spawn // 50) < SORTIE_MIN_TIME:
            is_ignored = True

    killboard_pvp = defaultdict(int)
    killboard_pve = defaultdict(int)

    ak_total = 0
    fak_total = 0
    ak_assist = 0
    gk_total = 0
    fgk_total = 0
    score = 0

    for targets in sortie.killboard.values():
        for target in targets:
            is_friendly = sortie.coal_id == target.coal_id

            if not is_friendly:
                score += mission.score_dict[target.cls]
                if target.cls_base == 'aircraft':
                    ak_total += 1
                elif target.cls_base in ('block', 'vehicle', 'tank'):
                    gk_total += 1
                if target.sortie:
                    killboard_pvp[target.cls] += 1
                else:
                    killboard_pve[target.cls] += 1
            else:
                cls_name = 'f_%s' % target.cls
                if target.cls_base == 'aircraft':
                    fak_total += 1
                elif target.cls_base in ('block', 'vehicle', 'tank'):
                    fgk_total += 1
                if target.sortie:
                    killboard_pvp[cls_name] += 1
                else:
                    killboard_pve[cls_name] += 1

    for targets in sortie.assistboard.values():
        for target in targets:
            if target.cls_base == 'aircraft':
                # френдов не считаем
                if sortie.coal_id == target.coal_id:
                    continue
                ak_assist += 1
                score += mission.score_dict['ak_assist']

    new_sortie = Sortie(
        profile=profile,
        player=player,
        tour=mission.tour,
        mission=mission,
        nickname=sortie.nickname,
        date_start=sortie_date_start,
        date_end=sortie_date_end,
        flight_time=flight_time,
        aircraft_id=sortie_aircraft_id,
        fuel=sortie.fuel or 0,
        skin=sortie.skin,
        payload_id=sortie.payload_id,
        weapon_mods_id=sortie.weapon_mods_id,
        # ======================== MODDED PART BEGIN
        ammo=create_ammo(sortie),
        # ======================== MODDED PART END
        coalition=sortie.coal_id,
        country=sortie.country_id,
        is_airstart=sortie.is_airstart,

        ak_total=ak_total,
        gk_total=gk_total,
        fak_total=fak_total,
        fgk_total=fgk_total,
        ak_assist=ak_assist,

        killboard_pvp=killboard_pvp,
        killboard_pve=killboard_pve,

        status=sortie.sortie_status.status,
        aircraft_status=sortie.aircraft_status.status,
        bot_status=sortie.bot_status.status,

        is_bailout=sortie.is_bailout,
        is_captured=sortie.is_captured,
        is_disco=sortie.is_disco,

        score=score,
        score_dict={'basic': score},
        ratio=sortie.ratio,
        damage=round(sortie.aircraft_damage, 2),
        wound=round(sortie.bot_damage, 2),
        debug={'aircraft_id': sortie.aircraft_id, 'bot_id': sortie.bot_id},
        is_ignored=is_ignored,
    )

    return new_sortie


# ======================== MODDED PART BEGIN
# Here we additionally inject ammo_breakdown.
def create_ammo(sortie):

    result = {'used_cartridges': sortie.used_cartridges,
              'used_bombs': sortie.used_bombs,
              'used_rockets': sortie.used_rockets,
              'used_shells': sortie.used_shells,
              'hit_bullets': sortie.hit_bullets,
              'hit_bombs': sortie.hit_bombs,
              'hit_rockets': sortie.hit_rockets,
              'hit_shells': sortie.hit_shells}

    if hasattr(sortie, 'ammo_breakdown'):
        result['ammo_breakdown'] = sortie.ammo_breakdown

    return result
# ======================== MODDED PART END

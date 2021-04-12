from collections import defaultdict
from django.conf import settings
from datetime import timedelta
from stats.models import Sortie
from .variant_utils import is_jabo, is_fighter
from .models import SortieAugmentation

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
                score += mission.score_dict[target.cls]['ai' if target.is_ai() else 'base']
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
                score += mission.score_dict['ak_assist']['base']

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

    new_sortie.save()

    cls = 'placeholder'
    if is_fighter(new_sortie):
        cls = 'light'
    elif new_sortie.aircraft.cls == "aircraft_medium" or is_jabo(new_sortie):
        cls = 'medium'
    elif new_sortie.aircraft.cls == "aircraft_heavy":
        cls = 'heavy'

    SortieAugmentation(sortie=new_sortie, cls=cls).save()

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


def update_general(player, new_sortie):
    flight_time_add = 0
    if not new_sortie.is_not_takeoff:
        player.sorties_total += 1
        flight_time_add = new_sortie.flight_time
    player.flight_time += flight_time_add

    relive_add = 1 if new_sortie.is_relive else 0
    player.relive += relive_add

    player.ak_total += new_sortie.ak_total
    player.fak_total += new_sortie.fak_total
    player.gk_total += new_sortie.gk_total
    player.fgk_total += new_sortie.fgk_total
    player.ak_assist += new_sortie.ak_assist
    player.score += new_sortie.score

    try:
        # ======================== MODDED PART BEGIN
        if is_fighter(new_sortie):
            player.score_light += new_sortie.score
            player.flight_time_light += flight_time_add
            player.relive_light += relive_add
        elif new_sortie.aircraft.cls == "aircraft_medium" or is_jabo(new_sortie):
            # ======================== MODDED PART END
            player.score_medium += new_sortie.score
            player.flight_time_medium += flight_time_add
            player.relive_medium += relive_add
        elif new_sortie.aircraft.cls == "aircraft_heavy":
            player.score_heavy += new_sortie.score
            player.flight_time_heavy += flight_time_add
            player.relive_heavy += relive_add
    except AttributeError:
        pass  # Some player objects have no score or relive attributes for light/medium/heavy aircraft.

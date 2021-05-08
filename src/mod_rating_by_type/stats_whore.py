from collections import defaultdict
from django.conf import settings
from datetime import timedelta
from stats.models import Sortie
from .variant_utils import decide_adjusted_cls
from .models import SortieAugmentation
from .config_modules import (module_active, MODULE_UNDAMAGED_BAILOUT_PENALTY, MODULE_FLIGHT_TIME_BONUS,
                             MODULE_ADJUSTABLE_BONUSES_AND_PENALTIES, MODULE_REARM_ACCURACY_WORKAROUND,
                             MODULE_BAILOUT_ACCURACY_WORKAROUND)
from stats import stats_whore as old_stats_whore

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

    # ======================== MODDED PART BEGIN
    score, score_dict = adjust_base_score_modules(sortie, player, flight_time, score, mission.score_dict)
    # ======================== MODDED PART END

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
        # ======================== MODDED PART BEGIN
        score_dict=score_dict,
        # ======================== MODDED PART END
        ratio=sortie.ratio,
        damage=round(sortie.aircraft_damage, 2),
        wound=round(sortie.bot_damage, 2),
        debug={'aircraft_id': sortie.aircraft_id, 'bot_id': sortie.bot_id},
        is_ignored=is_ignored,
    )

    new_sortie.save()

    # ======================== MODDED PART BEGIN
    cls = decide_adjusted_cls(new_sortie, touch_db=True)
    SortieAugmentation(sortie=new_sortie, cls=cls).save()

    new_sortie.takeoff_count = 0
    if hasattr(sortie.aircraft, 'takeoff_count'):
        new_sortie.takeoff_count = sortie.aircraft.takeoff_count
    # ======================== MODDED PART END

    return new_sortie


# ======================== MODDED PART BEGIN
def adjust_base_score_modules(sortie, player, flight_time, score, bonuses_score_dict):
    score_dict = {}
    adjusted_score = score

    if module_active(MODULE_FLIGHT_TIME_BONUS):
        flight_time_bonus = int(flight_time / bonuses_score_dict['mod_flight_time_bonus']['base'])
        adjusted_score += flight_time_bonus
        score_dict['flight_time_bonus'] = flight_time_bonus

    if module_active(MODULE_UNDAMAGED_BAILOUT_PENALTY):
        # Check for a bail where no damage was taken from anyone else
        if sortie.is_bailout and not (sortie.aircraft_damage or sortie.bot_damage):
            penalty = min(score, bonuses_score_dict['mod_undmg_bailout_score']['base'])
            adjusted_score -= penalty
            score_dict['undamagedbailout_penalty'] = penalty

            # This technically should be in "update_fairplay" function.
            # Updating it here avoids monkey patching that function
            player.fairplay -= bonuses_score_dict['mod_undmg_bailout_fair']['base']

    score_dict['basic'] = adjusted_score

    return adjusted_score, score_dict


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


# Monkey patched in stats_whore.
def update_bonus_score(new_sortie):
    if not module_active(MODULE_ADJUSTABLE_BONUSES_AND_PENALTIES):
        old_stats_whore.old_update_bonus_score(new_sortie)
        return

    bonuses_score_dict = new_sortie.mission.score_dict

    # бонус процент
    bonus_pct = 0
    bonus_dict = {}
    penalty_pct = 0

    # бонусы получают только "честные" игроки
    if new_sortie.fairplay == 100:
        if new_sortie.is_landed:
            bonus = bonuses_score_dict['mod_bonus_landed']['base']
            bonus_pct += bonus
            bonus_dict['landed'] = bonus
        if new_sortie.coalition == new_sortie.mission.winning_coalition:
            bonus = bonuses_score_dict['mod_bonus_winning_coal']['base']
            bonus_pct += bonus
            bonus_dict['winning_coalition'] = bonus
        if new_sortie.is_in_flight:
            bonus = bonuses_score_dict['mod_bonus_in_flight']['base']
            bonus_pct += bonus
            bonus_dict['in_flight'] = bonus
    bonus_dict['total'] = bonus_pct

    # ставим базовые очки т.к. функция может вызваться несколько раз
    new_sortie.score = new_sortie.score_dict['basic']

    if new_sortie.is_dead:
        penalty_pct = bonuses_score_dict['mod_penalty_dead']['base']
    elif new_sortie.is_captured:
        penalty_pct = bonuses_score_dict['mod_penalty_captured']['base']
    elif new_sortie.is_bailout:
        penalty_pct = bonuses_score_dict['mod_penalty_bailout']['base']
    elif new_sortie.is_shotdown:
        penalty_pct = bonuses_score_dict['mod_penalty_shotdown']['base']
    new_sortie.score = int(new_sortie.score * ((100 - penalty_pct) / 100))
    new_sortie.score_dict['penalty_pct'] = penalty_pct

    new_sortie.bonus = bonus_dict
    bonus_score = new_sortie.score * bonus_pct // 100
    new_sortie.score_dict['bonus'] = bonus_score
    new_sortie.score += bonus_score
    penalty_score = new_sortie.score * (100 - new_sortie.fairplay) // 100
    new_sortie.score_dict['penalty'] = penalty_score
    new_sortie.score -= penalty_score
    # new_sortie.save()


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
        cls = decide_adjusted_cls(new_sortie)
        if cls == 'light':
            player.score_light += new_sortie.score
            player.flight_time_light += flight_time_add
            player.relive_light += relive_add
        elif cls == 'medium':
            # ======================== MODDED PART END
            player.score_medium += new_sortie.score
            player.flight_time_medium += flight_time_add
            player.relive_medium += relive_add
        elif cls == "heavy":
            player.score_heavy += new_sortie.score
            player.flight_time_heavy += flight_time_add
            player.relive_heavy += relive_add
    except AttributeError:
        pass  # Some player objects have no score or relive attributes for light/medium/heavy aircraft.


def update_ammo(sortie, player):
    # ======================== MODDED PART BEGIN
    if module_active(MODULE_REARM_ACCURACY_WORKAROUND):
        if sortie.takeoff_count > 1:
            return

    if module_active(MODULE_BAILOUT_ACCURACY_WORKAROUND):
        if sortie.is_bailout:
            return
    # ======================== MODDED PART END
    # в логах есть баги, по окончание вылета у самолета может быть больше боемкомплекта чем было вначале
    if sortie.ammo['used_cartridges'] >= sortie.ammo['hit_bullets']:
        player.ammo['used_cartridges'] += sortie.ammo['used_cartridges']
        player.ammo['hit_bullets'] += sortie.ammo['hit_bullets']
    if sortie.ammo['used_bombs'] >= sortie.ammo['hit_bombs']:
        player.ammo['used_bombs'] += sortie.ammo['used_bombs']
        player.ammo['hit_bombs'] += sortie.ammo['hit_bombs']
    if sortie.ammo['used_rockets'] >= sortie.ammo['hit_rockets']:
        player.ammo['used_rockets'] += sortie.ammo['used_rockets']
        player.ammo['hit_rockets'] += sortie.ammo['hit_rockets']
    if sortie.ammo['used_shells'] >= sortie.ammo['hit_shells']:
        player.ammo['used_shells'] += sortie.ammo['used_shells']
        player.ammo['hit_shells'] += sortie.ammo['hit_shells']

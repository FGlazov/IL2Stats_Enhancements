from collections import defaultdict
from django.conf import settings
from datetime import timedelta
from stats.models import Sortie, KillboardPvP, LogEntry
from .variant_utils import decide_adjusted_cls
from .models import SortieAugmentation, FilteredPlayerMission, FilteredPlayerAircraft, FilteredVLife, FilteredPlayer
from .config_modules import (module_active, MODULE_UNDAMAGED_BAILOUT_PENALTY, MODULE_FLIGHT_TIME_BONUS,
                             MODULE_ADJUSTABLE_BONUSES_AND_PENALTIES, MODULE_REARM_ACCURACY_WORKAROUND,
                             MODULE_BAILOUT_ACCURACY_WORKAROUND, MODULE_SPLIT_RANKINGS)
from stats import stats_whore as old_stats_whore

from .rewards import reward_sortie, reward_vlife, reward_mission, reward_tour
from stats.stats_whore import (update_killboard, update_status, stats_whore, cleanup, collect_mission_reports,
                               update_online, cleanup_registration)
from .background_jobs.run_background_jobs import run_background_jobs, reset_corrupted_data, \
    retro_split_rankings_compute_running
import sys
from core import __version__
from stats.logger import logger
import time
import django

MISSION_REPORT_PATH = settings.MISSION_REPORT_PATH
SORTIE_MIN_TIME = settings.SORTIE_MIN_TIME
SORTIE_DISCO_MIN_TIME = settings.SORTIE_DISCO_MIN_TIME
SORTIE_DAMAGE_DISCO_TIME = settings.SORTIE_DAMAGE_DISCO_TIME


def main():
    logger.info('IL2 stats {stats}, Python {python}, Django {django}'.format(
        stats=__version__, python=sys.version[0:5], django=django.get_version()))

    # TODO переделать на проверку по времени создания файлов
    processed_reports = []

    waiting_new_report = False
    online_timestamp = 0

    # ======================== MODDED PART BEGIN
    reset_corrupted_data()
    # ======================== MODDED PART END

    while True:
        new_reports = []
        for m_report_file in MISSION_REPORT_PATH.glob('missionReport*[[]0[]].txt'):
            if m_report_file.name not in processed_reports:
                new_reports.append(m_report_file)

        if len(new_reports) > 1:
            waiting_new_report = False
            # обрабатываем все логи кроме последней миссии
            for m_report_file in new_reports[:-1]:
                stats_whore(m_report_file=m_report_file)
                cleanup(m_report_file=m_report_file)
                processed_reports.append(m_report_file.name)
            continue
        elif len(new_reports) == 1:
            m_report_file = new_reports[0]
            m_report_files = collect_mission_reports(m_report_file=m_report_file)
            online_timestamp = update_online(m_report_files=m_report_files, online_timestamp=online_timestamp)
            # если последний файл был создан более 2х минут назад - обрабатываем его
            if time.time() - m_report_files[-1].stat().st_mtime > 120:
                waiting_new_report = False
                # ======================== MODDED PART BEGIN
                backfill_log = True
                # ======================== MODDED PART END
                stats_whore(m_report_file=m_report_file)
                cleanup(m_report_file=m_report_file)
                processed_reports.append(m_report_file.name)
                continue
        # ======================== MODDED PART BEGIN
        background_work_done = run_background_jobs()
        if background_work_done:
            continue
        # ======================== MODDED PART END

        if not waiting_new_report:
            logger.info('waiting new report...')
        waiting_new_report = True

        # удаляем юзеров которые не активировали свои регистрации в течении определенного времени
        cleanup_registration()

        # в идеале новые логи появляются как минимум раз в 30 секунд
        time.sleep(30)


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

    # for disco sorties, if the total departure time is less than the one set by the config, disco = bailout sortie (time is set in seconds)

    if SORTIE_DISCO_MIN_TIME and sortie.is_disco:
        if (sortie_tik_last // 50) - (sortie.tik_takeoff // 50) < SORTIE_DISCO_MIN_TIME:
            sortie.is_discobailout = True
            sortie.is_disco = False

    # in case of disconect if time of damage to airplane happend outside of time set in conf.ini file, sortie is considered disco,
    # if time of damage happend inside time set, sortie will be considered captured (time is set in seconds)

    if SORTIE_DAMAGE_DISCO_TIME and sortie.is_damageddisco:

        if (sortie.tik_last // 50) - (sortie.tik_lastdamage // 50) > SORTIE_DAMAGE_DISCO_TIME:
            sortie.is_disco = True
            sortie.is_damageddisco = False
    # for damaged disco sorties, if the total departure time is less than the one set by the config for disco_min_time, damageddisco = bailout sortie
            if (sortie_tik_last // 50) - (sortie.tik_takeoff // 50) < SORTIE_DISCO_MIN_TIME:
                sortie.is_discobailout = True
                sortie.is_disco = False
                sortie.is_damageddisco = False

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

        is_bailout=sortie.is_bailout or sortie.is_discobailout,
        is_captured=sortie.is_captured or sortie.is_damageddisco,
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
    new_sortie.turret_kills = 0
    if hasattr(sortie.aircraft, 'turret_kills'):
        new_sortie.turret_kills = len(sortie.aircraft.turret_kills)
    cls = decide_adjusted_cls(new_sortie, touch_db=True)
    SortieAugmentation(sortie=new_sortie, cls=cls).save()
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


# Monkey patched in stats_whore.
def update_bonus_score(new_sortie):
    if not module_active(MODULE_ADJUSTABLE_BONUSES_AND_PENALTIES):
        old_stats_whore.old_update_bonus_score(new_sortie)
    else:

        bonuses_score_dict = new_sortie.mission.score_dict

        # бонус процент
        bonus_pct = 0
        bonus_dict = {}
        penalty_pct = 0
        is_aircraft = new_sortie.aircraft.cls_base == 'aircraft' or new_sortie.aircraft.cls == 'aircraft_turret'

        # бонусы получают только "честные" игроки
        if new_sortie.fairplay == 100:
            if new_sortie.is_landed:
                bonus_key = 'mod_bonus_landed' if is_aircraft else 'tank_bonus_landed'
                bonus = bonuses_score_dict[bonus_key]['base']
                bonus_pct += bonus
                bonus_dict['landed'] = bonus
            if new_sortie.coalition == new_sortie.mission.winning_coalition:
                bonus_key = 'mod_bonus_winning_coal' if is_aircraft else 'tank_bonus_winning_coa'
                bonus = bonuses_score_dict[bonus_key]['base']
                bonus_pct += bonus
                bonus_dict['winning_coalition'] = bonus
            if new_sortie.is_in_flight:
                bonus_key = 'mod_bonus_in_flight' if is_aircraft else 'tank_bonus_in_flight'
                bonus = bonuses_score_dict[bonus_key]['base']
                bonus_pct += bonus
                bonus_dict['in_flight'] = bonus
            if new_sortie.is_not_takeoff and not is_aircraft:
                bonus_key = 'tank_bonus_in_service'
                bonus = bonuses_score_dict[bonus_key]['base']
                bonus_pct += bonus
                bonus_dict['in_service'] = bonus
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

    cls = decide_adjusted_cls(new_sortie)
    if (module_active(MODULE_SPLIT_RANKINGS) and cls in {'light', 'medium', 'heavy'}
            and not retro_split_rankings_compute_running()):
        increment_subtype_persona(new_sortie, cls)
        sortie_augmentation = new_sortie.SortieAugmentation_MOD_SPLIT_RANKINGS
        sortie_augmentation.computed_filtered_player = True
        sortie_augmentation.save()


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


def update_ammo(sortie, player, retroactive_compute=False):
    # ======================== MODDED PART BEGIN
    if module_active(MODULE_REARM_ACCURACY_WORKAROUND):
        if retroactive_compute:
            takeoff_count = LogEntry.objects.filter(
                act_sortie_id=sortie.id,
                type='takeoff'
            ).count()
            if takeoff_count > 1:
                return  # Bug work around. Rearming (and as such taking off twice) resets ammo used according to logs.
        elif hasattr(sortie, 'takeoff_count') and sortie.takeoff_count > 1:
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


# Monkey patched into update_sortie of stats_whore.
def update_sortie(new_sortie, player_mission, player_aircraft, vlife, player=None, retroactive_compute=False):
    # ======================== MODDED PART BEGIN
    if player is None:
        player = new_sortie.player
    # ======================== MODDED PART END

    if not player.date_first_sortie:
        player.date_first_sortie = new_sortie.date_start
        player.date_last_combat = new_sortie.date_start
    player.date_last_sortie = new_sortie.date_start

    if not vlife.date_first_sortie:
        vlife.date_first_sortie = new_sortie.date_start
        vlife.date_last_combat = new_sortie.date_start
    vlife.date_last_sortie = new_sortie.date_start

    # если вылет был окончен диско - результаты вылета не добавляться к общему профилю
    if new_sortie.is_disco:
        player.disco += 1
        player_mission.disco += 1
        player_aircraft.disco += 1
        vlife.disco += 1
        return
    # если вылет игнорируется по каким либо причинам
    elif new_sortie.is_ignored:
        return

    # если в вылете было что-то уничтожено - считаем его боевым
    if new_sortie.score:
        player.date_last_combat = new_sortie.date_start
        vlife.date_last_combat = new_sortie.date_start

    vlife.status = new_sortie.status
    vlife.aircraft_status = new_sortie.aircraft_status
    vlife.bot_status = new_sortie.bot_status

    # TODO проверить как это отработает для вылетов стрелков
    if not new_sortie.is_not_takeoff:
        player.sorties_coal[new_sortie.coalition] += 1
        player_mission.sorties_coal[new_sortie.coalition] += 1
        vlife.sorties_coal[new_sortie.coalition] += 1

        if player.squad:
            player.squad.sorties_coal[new_sortie.coalition] += 1

        if new_sortie.aircraft.cls_base == 'aircraft':
            if new_sortie.aircraft.cls in player.sorties_cls:
                player.sorties_cls[new_sortie.aircraft.cls] += 1
            else:
                player.sorties_cls[new_sortie.aircraft.cls] = 1

            if new_sortie.aircraft.cls in vlife.sorties_cls:
                vlife.sorties_cls[new_sortie.aircraft.cls] += 1
            else:
                vlife.sorties_cls[new_sortie.aircraft.cls] = 1

            if player.squad:
                if new_sortie.aircraft.cls in player.squad.sorties_cls:
                    player.squad.sorties_cls[new_sortie.aircraft.cls] += 1
                else:
                    player.squad.sorties_cls[new_sortie.aircraft.cls] = 1

    update_general(player=player, new_sortie=new_sortie)
    update_general(player=player_mission, new_sortie=new_sortie)
    update_general(player=player_aircraft, new_sortie=new_sortie)
    update_general(player=vlife, new_sortie=new_sortie)
    if player.squad:
        update_general(player=player.squad, new_sortie=new_sortie)

    update_ammo(sortie=new_sortie, player=player)
    update_ammo(sortie=new_sortie, player=player_mission)
    update_ammo(sortie=new_sortie, player=player_aircraft)
    update_ammo(sortie=new_sortie, player=vlife)

    update_killboard(player=player, killboard_pvp=new_sortie.killboard_pvp,
                     killboard_pve=new_sortie.killboard_pve)
    update_killboard(player=player_mission, killboard_pvp=new_sortie.killboard_pvp,
                     killboard_pve=new_sortie.killboard_pve)
    update_killboard(player=player_aircraft, killboard_pvp=new_sortie.killboard_pvp,
                     killboard_pve=new_sortie.killboard_pve)
    update_killboard(player=vlife, killboard_pvp=new_sortie.killboard_pvp,
                     killboard_pve=new_sortie.killboard_pve)

    player.streak_current = vlife.ak_total
    player.streak_max = max(player.streak_max, player.streak_current)
    player.streak_ground_current = vlife.gk_total
    player.streak_ground_max = max(player.streak_ground_max, player.streak_ground_current)
    player.score_streak_current = vlife.score
    player.score_streak_current_heavy = vlife.score_heavy
    player.score_streak_current_medium = vlife.score_medium
    player.score_streak_current_light = vlife.score_light
    player.score_streak_max = max(player.score_streak_max, player.score_streak_current)
    player.score_streak_max_heavy = max(player.score_streak_max_heavy, player.score_streak_current_heavy)
    player.score_streak_max_medium = max(player.score_streak_max_medium, player.score_streak_current_medium)
    player.score_streak_max_light = max(player.score_streak_max_light, player.score_streak_current_light)

    player.sorties_streak_current = vlife.sorties_total
    player.sorties_streak_max = max(player.sorties_streak_max, player.sorties_streak_current)
    player.ft_streak_current = vlife.flight_time
    player.ft_streak_max = max(player.ft_streak_max, player.ft_streak_current)

    if new_sortie.is_relive:
        player.streak_current = 0
        player.streak_ground_current = 0
        player.score_streak_current = 0
        player.score_streak_current_heavy = 0
        player.score_streak_current_medium = 0
        player.score_streak_current_light = 0
        player.sorties_streak_current = 0
        player.ft_streak_current = 0
        player.lost_aircraft_current = 0
    else:
        if new_sortie.is_lost_aircraft:
            player.lost_aircraft_current += 1

    player.sortie_max_ak = max(player.sortie_max_ak, new_sortie.ak_total)
    player.sortie_max_gk = max(player.sortie_max_gk, new_sortie.gk_total)

    update_status(new_sortie=new_sortie, player=player)
    update_status(new_sortie=new_sortie, player=player_mission)
    update_status(new_sortie=new_sortie, player=player_aircraft)
    update_status(new_sortie=new_sortie, player=vlife)
    if player.squad:
        update_status(new_sortie=new_sortie, player=player.squad)


# ======================== MODDED PART BEGIN
def increment_subtype_persona(sortie, cls):
    # TODO: At some point also calculate the killboard.
    #   At the moment there seems to be no way to do it outside of monkey patching stats_whore or retroactive computing.
    #   Perhaps there is a nicer way to calculate it...
    player = FilteredPlayer.objects.get_or_create(
        profile_id=sortie.player.profile.id,
        tour_id=sortie.tour.id,
        type='pilot',
        cls=cls,
    )[0]

    _profile_id = sortie.profile.id
    mission = sortie.mission

    player_mission = FilteredPlayerMission.objects.get_or_create(
        profile_id=_profile_id,
        player=player,
        mission_id=mission.id,
        cls=cls
    )[0]
    player_aircraft = FilteredPlayerAircraft.objects.get_or_create(
        profile_id=_profile_id,
        player=player,
        aircraft_id=sortie.aircraft.id,
        cls=cls
    )[0]
    vlife = FilteredVLife.objects.get_or_create(
        profile_id=_profile_id,
        player=player,
        tour_id=sortie.tour.id,
        relive=0,
        cls=cls
    )[0]

    update_sortie(new_sortie=sortie, player_mission=player_mission, player_aircraft=player_aircraft, vlife=vlife,
                  player=player)

    player.save()
    player_mission.save()
    player_aircraft.save()
    vlife.save()
    sortie.save()

    reward_sortie(sortie=sortie, player=player)
    reward_vlife(vlife=vlife, player=player)
    reward_mission(player_mission=player_mission, player=player)
    reward_tour(player=player)

# ======================== MODDED PART END
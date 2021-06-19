import time
from stats.stats_whore import (stats_whore, cleanup, collect_mission_reports, update_killboard_pvp, create_new_sortie,
                               backup_log,
                               get_tour, update_fairplay, update_bonus_score, update_sortie, create_profiles)
from stats.rewards import reward_sortie, reward_tour, reward_mission, reward_vlife
from stats.logger import logger
from stats.online import update_online
from stats.models import LogEntry, Mission, PlayerMission, VLife, PlayerAircraft, Object, Score, Sortie, Tour, Player
from .background_jobs.run_background_jobs import run_background_jobs, reset_corrupted_data
from .aircraft_stats_compute import process_aircraft_stats
from users.utils import cleanup_registration
from django.conf import settings
from django.db.models import Q, F, Max, Count
from core import __version__
from .aircraft_mod_models import (AircraftBucket, AircraftKillboard, SortieAugmentation)
import sys
import django
import pytz
from datetime import datetime, timedelta
from types import MappingProxyType
from mission_report.report import MissionReport
from mission_report.statuses import LifeStatus
from collections import defaultdict
from django.db import transaction
import operator
import config

from .variant_utils import get_sortie_type, has_bomb_variant, has_juiced_variant

MISSION_REPORT_BACKUP_PATH = settings.MISSION_REPORT_BACKUP_PATH
MISSION_REPORT_BACKUP_DAYS = settings.MISSION_REPORT_BACKUP_DAYS
MISSION_REPORT_DELETE = settings.MISSION_REPORT_DELETE
MISSION_REPORT_PATH = settings.MISSION_REPORT_PATH
NEW_TOUR_BY_MONTH = settings.NEW_TOUR_BY_MONTH
TIME_ZONE = pytz.timezone(settings.MISSION_REPORT_TZ)

WIN_BY_SCORE = settings.WIN_BY_SCORE
WIN_SCORE_MIN = settings.WIN_SCORE_MIN
WIN_SCORE_RATIO = settings.WIN_SCORE_RATIO
SORTIE_MIN_TIME = settings.SORTIE_MIN_TIME


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


@transaction.atomic
def stats_whore(m_report_file):
    """
    :type m_report_file: Path
    """
    mission_timestamp = int(time.mktime(time.strptime(m_report_file.name[14:-8], '%Y-%m-%d_%H-%M-%S')))

    if Mission.objects.filter(timestamp=mission_timestamp).exists():
        logger.info('{mission} - exists in the DB'.format(mission=m_report_file.stem))
        return
    logger.info('{mission} - processing new report'.format(mission=m_report_file.stem))

    m_report_files = collect_mission_reports(m_report_file=m_report_file)

    real_date = TIME_ZONE.localize(datetime.fromtimestamp(mission_timestamp))
    real_date = real_date.astimezone(pytz.UTC)

    objects = MappingProxyType({obj['log_name']: obj for obj in Object.objects.values()})
    # classes = MappingProxyType({obj['cls']: obj['cls_base'] for obj in objects.values()})
    score_dict = MappingProxyType({s.key: {'base': s.get_value(), 'ai': s.get_ai_value()} for s in Score.objects.all()})

    m_report = MissionReport(objects=objects)
    m_report.processing(files=m_report_files)

    backup_log(name=m_report_file.name, lines=m_report.lines, date=real_date)

    if not m_report.is_correctly_completed:
        logger.info('{mission} - mission has not been completed correctly'.format(mission=m_report_file.stem))

    tour = get_tour(date=real_date)

    mission = Mission.objects.create(
        tour_id=tour.id,
        name=m_report.file_path.replace('\\', '/').split('/')[-1].rsplit('.', 1)[0],
        path=m_report.file_path,
        date_start=real_date,
        date_end=real_date + timedelta(seconds=m_report.tik_last // 50),
        duration=m_report.tik_last // 50,
        timestamp=mission_timestamp,
        preset=m_report.preset_id,
        settings=m_report.settings,
        is_correctly_completed=m_report.is_correctly_completed,
        score_dict=dict(score_dict),
    )
    if m_report.winning_coal_id:
        mission.winning_coalition = m_report.winning_coal_id
        mission.win_reason = 'task'
        mission.save()

    # собираем/создаем профили игроков и сквадов
    profiles, players_pilots, players_gunners, players_tankmans, squads = create_profiles(tour=tour,
                                                                                          sorties=m_report.sorties)

    players_aircraft = defaultdict(dict)
    players_mission = {}
    players_killboard = {}

    coalition_score = {1: 0, 2: 0}
    new_sorties = []
    for sortie in m_report.sorties:
        sortie_aircraft_id = objects[sortie.aircraft_name]['id']
        profile = profiles[sortie.account_id]
        if sortie.cls_base == 'aircraft':
            player = players_pilots[sortie.account_id]
        elif sortie.cls == 'aircraft_turret':
            player = players_gunners[sortie.account_id]
        elif sortie.cls in ('tank_light', 'tank_heavy', 'tank_medium', 'tank_turret', 'truck'):
            player = players_tankmans[sortie.account_id]
        else:
            continue

        squad = squads[profile.squad_id] if profile.squad else None
        player.squad = squad

        new_sortie = create_new_sortie(mission=mission, sortie=sortie, profile=profile, player=player,
                                       sortie_aircraft_id=sortie_aircraft_id)
        update_fairplay(new_sortie=new_sortie)
        update_bonus_score(new_sortie=new_sortie)

        # не добавляем очки в сумму если было диско
        if not new_sortie.is_disco:
            coalition_score[new_sortie.coalition] += new_sortie.score

        new_sorties.append(new_sortie)
        # добавляем ссылку на запись в базе к объекту вылета, чтобы использовать в добавлении событий вылета
        sortie.sortie_db = new_sortie

    if not mission.winning_coalition and WIN_BY_SCORE:
        _coalition = sorted(coalition_score.items(), key=operator.itemgetter(1), reverse=True)
        max_coal, max_score = _coalition[0]
        min_coal, min_score = _coalition[1]
        # минимальное кол-во очков = 1
        min_score = min_score or 1
        if max_score >= WIN_SCORE_MIN and max_score / min_score >= WIN_SCORE_RATIO:
            mission.winning_coalition = max_coal
            mission.win_reason = 'score'
            mission.save()

    for new_sortie in new_sorties:
        _player_id = new_sortie.player.id
        _profile_id = new_sortie.profile.id

        player_mission = players_mission.setdefault(
            _player_id,
            PlayerMission.objects.get_or_create(profile_id=_profile_id, player_id=_player_id, mission_id=mission.id)[0]
        )

        player_aircraft = players_aircraft[_player_id].setdefault(
            new_sortie.aircraft.id,
            PlayerAircraft.objects.get_or_create(profile_id=_profile_id, player_id=_player_id,
                                                 aircraft_id=new_sortie.aircraft.id)[0]
        )

        vlife = VLife.objects.get_or_create(profile_id=_profile_id, player_id=_player_id, tour_id=tour.id, relive=0)[0]

        # если случилась победа по очкам - требуется обновить бонусы
        if mission.win_reason == 'score':
            update_bonus_score(new_sortie=new_sortie)

        update_sortie(new_sortie=new_sortie, player_mission=player_mission, player_aircraft=player_aircraft,
                      vlife=vlife)
        reward_sortie(sortie=new_sortie)

        vlife.save()
        reward_vlife(vlife)

        new_sortie.vlife_id = vlife.id
        new_sortie.save()

    # ===============================================================================
    mission.players_total = len(profiles)
    mission.pilots_total = len(players_pilots)
    mission.gunners_total = len(players_gunners)
    mission.save()

    for p in profiles.values():
        p.save()

    for p in players_pilots.values():
        p.save()
        reward_tour(player=p)

    for p in players_gunners.values():
        p.save()

    for p in players_tankmans.values():
        p.save()

    for aircrafts in players_aircraft.values():
        for a in aircrafts.values():
            a.save()

    for p in players_mission.values():
        p.save()
        reward_mission(player_mission=p)

    for s in squads.values():
        s.save()

    tour.save()

    for event in m_report.log_entries:
        params = {
            'mission_id': mission.id,
            'date': real_date + timedelta(seconds=event['tik'] // 50),
            'tik': event['tik'],
            'extra_data': {
                'pos': event.get('pos'),
            },
        }
        if event['type'] == 'respawn':
            params['type'] = 'respawn'
            params['act_object_id'] = event['sortie'].sortie_db.aircraft.id
            params['act_sortie_id'] = event['sortie'].sortie_db.id
        elif event['type'] == 'end':
            params['type'] = 'end'
            params['act_object_id'] = event['sortie'].sortie_db.aircraft.id
            params['act_sortie_id'] = event['sortie'].sortie_db.id
        elif event['type'] == 'takeoff':
            params['type'] = 'takeoff'
            params['act_object_id'] = event['aircraft'].sortie.sortie_db.aircraft.id
            params['act_sortie_id'] = event['aircraft'].sortie.sortie_db.id
        elif event['type'] == 'landed':
            params['act_object_id'] = event['aircraft'].sortie.sortie_db.aircraft.id
            params['act_sortie_id'] = event['aircraft'].sortie.sortie_db.id
            if event['is_rtb'] and not event['is_killed']:
                params['type'] = 'landed'
            else:
                if event['status'] == LifeStatus.destroyed:
                    params['type'] = 'crashed'
                else:
                    params['type'] = 'ditched'
        elif event['type'] == 'bailout':
            params['type'] = 'bailout'
            params['act_object_id'] = event['bot'].sortie.sortie_db.aircraft.id
            params['act_sortie_id'] = event['bot'].sortie.sortie_db.id
        elif event['type'] == 'damage':
            params['extra_data']['damage'] = event['damage']
            params['extra_data']['is_friendly_fire'] = event['is_friendly_fire']
            if event['target'].cls_base == 'crew':
                params['type'] = 'wounded'
            else:
                params['type'] = 'damaged'
            if event['attacker']:
                if ((event['attacker'].cls == 'tank_turret' or (event['attacker'].cls_base == 'tank'))
                        and event['attacker'].parent and event['attacker'].parent.sortie):
                    # Credit the damage to the tank driver.
                    params['act_object_id'] = event[
                        'attacker'].parent.sortie.sortie_db.aircraft.id  # This is a tank, not an aircraft!
                    params['act_sortie_id'] = event['attacker'].parent.sortie.sortie_db.id
                elif event['attacker'].sortie:
                    params['act_object_id'] = event['attacker'].sortie.sortie_db.aircraft.id
                    params['act_sortie_id'] = event['attacker'].sortie.sortie_db.id
                else:
                    params['act_object_id'] = objects[event['attacker'].log_name]['id']
            if event['target'].sortie:
                params['cact_object_id'] = event['target'].sortie.sortie_db.aircraft.id
                params['cact_sortie_id'] = event['target'].sortie.sortie_db.id
            else:
                params['cact_object_id'] = objects[event['target'].log_name]['id']
        elif event['type'] == 'kill':
            params['extra_data']['is_friendly_fire'] = event['is_friendly_fire']
            if event['target'].cls_base == 'crew':
                params['type'] = 'killed'
            elif event['target'].cls_base == 'aircraft':
                params['type'] = 'shotdown'
            else:
                params['type'] = 'destroyed'
            if event['attacker']:
                if ((event['attacker'].cls == 'tank_turret' or (event['attacker'].cls_base == 'tank'))
                        and event['attacker'].parent and event['attacker'].parent.sortie):
                    # Credit the kill to the tank driver.
                    params['act_object_id'] = event[
                        'attacker'].parent.sortie.sortie_db.aircraft.id  # This is a tank, not an aircraft!
                    params['act_sortie_id'] = event['attacker'].parent.sortie.sortie_db.id
                elif event['attacker'].sortie:
                    params['act_object_id'] = event['attacker'].sortie.sortie_db.aircraft.id
                    params['act_sortie_id'] = event['attacker'].sortie.sortie_db.id
                else:
                    params['act_object_id'] = objects[event['attacker'].log_name]['id']
            if event['target'].sortie:
                params['cact_object_id'] = event['target'].sortie.sortie_db.aircraft.id
                params['cact_sortie_id'] = event['target'].sortie.sortie_db.id
            else:
                params['cact_object_id'] = objects[event['target'].log_name]['id']

        l = LogEntry.objects.create(**params)
        if l.type == 'shotdown' and l.act_sortie and l.cact_sortie and not l.act_sortie.is_disco and not l.extra_data.get('is_friendly_fire'):
            update_killboard_pvp(player=l.act_sortie.player, opponent=l.cact_sortie.player, players_killboard=players_killboard)

    for p in players_killboard.values():
        p.save()

    # ======================== MODDED PART BEGIN
    for sortie in new_sorties:
        process_aircraft_stats(sortie)
        process_aircraft_stats(sortie, player=sortie.player)
    # ======================== MODDED PART END
    logger.info('{mission} - processing finished'.format(mission=m_report_file.stem))

import time
from stats.stats_whore import (stats_whore, cleanup, collect_mission_reports, update_status, update_general,
                               update_ammo, update_killboard, update_killboard_pvp, create_new_sortie, backup_log,
                               get_tour, update_fairplay, update_bonus_score, update_sortie, create_profiles)
from stats.rewards import reward_sortie, reward_tour, reward_mission, reward_vlife
from stats.logger import logger
from stats.online import update_online
from stats.models import LogEntry, Mission, PlayerMission, VLife, PlayerAircraft, Object, Score, Sortie, Tour
from users.utils import cleanup_registration
from django.conf import settings
from django.db.models import Q, F, Max
from core import __version__
from .aircraft_mod_models import (AircraftBucket, AircraftKillboard, SortieAugmentation, has_juiced_variant,
                                  has_bomb_variant)
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

# ======================== MODDED PART BEGIN
RETRO_COMPUTE_FOR_LAST_HOURS = config.get_conf()['stats'].getint('retro_compute_for_last_tours')
if RETRO_COMPUTE_FOR_LAST_HOURS is None:
    RETRO_COMPUTE_FOR_LAST_HOURS = 10


# ======================== MODDED PART END

def main():
    logger.info('IL2 stats {stats}, Python {python}, Django {django}'.format(
        stats=__version__, python=sys.version[0:5], django=django.get_version()))

    # TODO переделать на проверку по времени создания файлов
    processed_reports = []

    waiting_new_report = False
    online_timestamp = 0

    # ======================== MODDED PART BEGIN
    backfill_aircraft_by_stats = True
    backfill_log = True
    # ======================== MODDED PART END

    while True:
        new_reports = []
        for m_report_file in MISSION_REPORT_PATH.glob('missionReport*[[]0[]].txt'):
            if m_report_file.name not in processed_reports:
                new_reports.append(m_report_file)

        if len(new_reports) > 1:
            waiting_new_report = False
            # ======================== MODDED PART BEGIN
            backfill_log = True
            # ======================== MODDED PART END
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
        if backfill_aircraft_by_stats:
            work_done = process_old_sorties_batch_aircraft_stats(backfill_log)
            backfill_aircraft_by_stats = work_done
            backfill_log = False
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
    score_dict = MappingProxyType({s.key: s.get_value() for s in Score.objects.all()})

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
        elif sortie.cls in ('tank_light', 'tank_heavy', 'tank_medium', 'tank_turret'):
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
        elif event['type'] == 'disco':
            params['type'] = 'disco'
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
                if event['attacker'].cls == 'tank_turret' and event['attacker'].parent.sortie:
                    # Credit the damage to the tank driver.
                    params['act_object_id'] = event['attacker'].parent.sortie.sortie_db.aircraft.id  # This is a tank, not an aircraft!
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
                if event['attacker'].cls == 'tank_turret' and event['attacker'].parent.sortie:
                    # Credit the kill to the tank driver.
                    params['act_object_id'] = event['attacker'].parent.sortie.sortie_db.aircraft.id  # This is a tank, not an aircraft!
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
        if l.type == 'shotdown' and l.act_sortie and l.cact_sortie and not l.act_sortie.is_disco and not l.extra_data.get(
                'is_friendly_fire'):
            update_killboard_pvp(player=l.act_sortie.player, opponent=l.cact_sortie.player,
                                 players_killboard=players_killboard)

    for p in players_killboard.values():
        p.save()

    # ======================== MODDED PART BEGIN
    for sortie in new_sorties:
        process_aircraft_stats(sortie)
    # ======================== MODDED PART END
    logger.info('{mission} - processing finished'.format(mission=m_report_file.stem))


# ======================== MODDED PART BEGIN
@transaction.atomic
def process_old_sorties_batch_aircraft_stats(backfill_log):
    max_id = Tour.objects.aggregate(Max('id'))['id__max']
    if max_id is None:  # Edge case: No tour yet
        return False
	
    tour_cutoff = max_id - RETRO_COMPUTE_FOR_LAST_HOURS

    backfill_sorties = (Sortie.objects.filter(SortieAugmentation_MOD_STATS_BY_AIRCRAFT__isnull=True,
                                              aircraft__cls_base='aircraft', tour__id__gte=tour_cutoff)
                        .order_by('-tour__id'))
    nr_left = backfill_sorties.count()
    if nr_left == 0:
        return False

    if backfill_log:
        logger.info('[mod_stats_by_aircraft]: Retroactively computing aircraft stats. {} sorties left to process.'
                    .format(nr_left))

    for sortie in backfill_sorties[0:1000]:
        process_aircraft_stats(sortie)

    if nr_left <= 1000:
        logger.info('[mod_stats_by_aircraft]: Completed retroactively computing aircraft stats.')

    return True


# This should be run after the other objects have been saved, otherwise it will not work.
def process_aircraft_stats(sortie):
    if not sortie.aircraft.cls_base == "aircraft":
        return

    bucket = (AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                   filter_type='NO_FILTER'))[0]

    has_subtype = has_juiced_variant(bucket.aircraft) or has_bomb_variant(bucket.aircraft)

    process_bucket(bucket, sortie, has_subtype, False)

    if has_subtype:
        filtered_bucket = (AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                                filter_type=get_sortie_type(sortie)))[0]
        process_bucket(filtered_bucket, sortie, True, True)


def process_bucket(bucket, sortie, has_subtype, is_subtype):
    if not sortie.is_not_takeoff:
        bucket.total_sorties += 1
        bucket.total_flight_time += sortie.flight_time
    bucket.kills += sortie.ak_total
    bucket.ground_kills += sortie.gk_total
    bucket.assists += sortie.ak_assist
    bucket.aircraft_lost += 1 if sortie.is_lost_aircraft else 0
    bucket.score += sortie.score
    bucket.deaths += 1 if sortie.is_dead else 0
    bucket.captures += 1 if sortie.is_captured else 0
    bucket.bailouts += 1 if sortie.is_bailout else 0
    bucket.ditches += 1 if sortie.is_ditched else 0
    bucket.landings += 1 if sortie.is_landed else 0
    bucket.in_flight += 1 if sortie.is_in_flight else 0
    bucket.crashes += 1 if sortie.is_crashed else 0
    bucket.shotdown += 1 if sortie.is_shotdown else 0
    bucket.coalition = sortie.coalition
    if sortie.ammo['used_cartridges']:
        bucket.ammo_shot += sortie.ammo['used_cartridges']
    if sortie.ammo['hit_bullets']:
        bucket.ammo_hit += sortie.ammo['hit_bullets']
    if sortie.ammo['used_bombs']:
        bucket.bomb_rocket_shot += sortie.ammo['used_bombs']
    if sortie.ammo['hit_bombs']:
        bucket.bomb_rocket_hit += sortie.ammo['hit_bombs']
    if sortie.ammo['used_rockets']:
        bucket.bomb_rocket_shot += sortie.ammo['used_rockets']
    if sortie.ammo['hit_rockets']:
        bucket.bomb_rocket_hit += sortie.ammo['hit_rockets']
    if sortie.damage:
        bucket.sorties_plane_was_hit += 1
        bucket.plane_survivability_counter += 1 if not sortie.is_lost_aircraft else 0
        bucket.pilot_survivability_counter += 1 if not sortie.is_relive else 0
    for key in sortie.killboard_pvp:
        value = sortie.killboard_pvp[key]
        if key in bucket.killboard_planes:
            bucket.killboard_planes[key] += value
        else:
            bucket.killboard_planes[key] = value
    for key in sortie.killboard_pve:
        value = sortie.killboard_pve[key]
        if key in bucket.killboard_ground:
            bucket.killboard_ground[key] += value
        else:
            bucket.killboard_ground[key] = value

    process_log_entries(bucket, sortie, has_subtype, is_subtype)

    sortie_augmentation = (SortieAugmentation.objects.get_or_create(sortie=sortie))[0]
    sortie_augmentation.sortie_stats_processed = True
    sortie_augmentation.save()


def process_log_entries(bucket, sortie, has_subtype, is_subtype):
    events = (LogEntry.objects
              .select_related('act_object', 'act_sortie', 'cact_object', 'cact_sortie')
              .filter(Q(act_sortie_id=sortie.id),
                      Q(type='shotdown') | Q(type='killed') | Q(type='damaged'),
                      act_object__cls_base='aircraft', cact_object__cls_base='aircraft',
                      # Disregard AI sorties
                      act_sortie_id__isnull=False, cact_sortie_id__isnull=False, )
              # Disregard friendly fire incidents.
              .exclude(act_sortie__coalition=F('cact_sortie__coalition')))

    enemies_damaged = set()
    enemies_shotdown = set()
    enemies_killed = set()

    for event in events:
        enemy_sortie = Sortie.objects.filter(id=event.cact_sortie_id).get()

        enemy_plane_sortie_pair = (event.cact_object, enemy_sortie)
        if event.type == 'damaged':
            enemies_damaged.add(enemy_plane_sortie_pair)
        elif event.type == 'shotdown':
            enemies_shotdown.add(enemy_plane_sortie_pair)
        elif event.type == 'killed':
            enemies_killed.add(enemy_plane_sortie_pair)

    enemy_buckets, kbs = update_from_entries(bucket, enemies_damaged, enemies_killed, enemies_shotdown,
                                             has_subtype, is_subtype)

    for killboard in kbs.values():
        killboard.save()
    for enemy_bucket in enemy_buckets.values():
        enemy_bucket.update_derived_fields()
        enemy_bucket.save()

    bucket.update_derived_fields()
    bucket.save()

    # LogEntry does not store what your turrets did. Only what turrets hit you.
    # So we parse all turret encounters from the perspective of the turret's plane.
    turret_events = (LogEntry.objects
                     .select_related('act_object', 'act_sortie', 'cact_object', 'cact_sortie')
                     .filter(Q(cact_sortie_id=sortie.id),
                             Q(type='shotdown') | Q(type='killed') | Q(type='damaged'),
                             act_object__cls='aircraft_turret', cact_object__cls_base='aircraft',
                             # Filter out AI kills from turret.
                             cact_sortie_id__isnull=False)

                     # Disregard friendly fire incidents.
                     .exclude(extra_data__is_friendly_fire=True))

    enemies_damaged = set()
    enemies_shotdown = set()
    enemies_killed = set()

    if len(turret_events) > 0 and not is_subtype:
        cache_turret_buckets = dict()

        for event in turret_events:
            turret_name = event.act_object.name
            if turret_name not in cache_turret_buckets:
                cache_turret_buckets[turret_name] = turret_to_aircraft_bucket(turret_name, bucket.tour)

            if event.type == 'damaged':
                enemies_damaged.add(turret_name)
            elif event.type == 'shotdown':
                enemies_shotdown.add(turret_name)
            elif event.type == 'killed':
                enemies_killed.add(turret_name)

        for turret_name in cache_turret_buckets:
            turret_bucket = cache_turret_buckets[turret_name]
            enemy_damaged = set()
            if turret_name in enemies_damaged:
                enemy_damaged.add((bucket.aircraft, sortie))
            enemy_shotdown = set()
            if turret_name in enemies_shotdown:
                enemy_shotdown.add((bucket.aircraft, sortie))
            enemy_killed = set()
            if turret_name in enemies_killed:
                enemy_killed.add((bucket.aircraft, sortie))

            buckets, kbs = update_from_entries(turret_bucket, enemy_damaged, enemy_killed, enemy_shotdown,
                                               # No bombers have subtypes
                                               False, False)

            turret_bucket.update_derived_fields()
            turret_bucket.save()
            for bucket in buckets.values():
                bucket.update_derived_fields()
                bucket.save()

            for kb in kbs.values():
                kb.save()


def update_from_entries(bucket, enemies_damaged, enemies_killed, enemies_shotdown, has_subtype, is_subtype):
    cache_kb = dict()
    cache_enemy_buckets_kb = dict()  # Helper cache needed in order to find buckets (quickly) inside get_killboard.
    for damaged_enemy in enemies_damaged:
        enemy_sortie = damaged_enemy[1]
        kbs = get_killboards(damaged_enemy, bucket, cache_kb, cache_enemy_buckets_kb)
        for kb in kbs:
            update_damaged_enemy(bucket, damaged_enemy, enemies_killed, enemies_shotdown, enemy_sortie, kb)

    cache_enemy_buckets = dict()
    for shotdown_enemy in enemies_shotdown:
        enemy_sortie = shotdown_enemy[1]
        enemy_sortie_type = get_sortie_type(enemy_sortie)

        subtype_enemy_bucket_key = (bucket.tour, shotdown_enemy[0], enemy_sortie_type)
        subtype_enemy_bucket = ensure_bucket_in_cache(cache_enemy_buckets, subtype_enemy_bucket_key)

        # There are in essecence three cases for the Elo Update:

        # Aircraft 1 and Aircraft 2 have no subtypes -> Just update elo directly.
        # Aircraft 1 and 2 have subtypes: Main types update each other. Subtypes update each other.
        # Aircraft 1 has subtypes, Aircraft 2 does not:
        # Aircraft 1 main type and subtype updates directly from Aircraft 2 only type
        # Aircraft 2 has "half an encounter" with aircraft 1 main type, and "half an encounter" with aircraft 1 subtype.

        if enemy_sortie_type == bucket.NO_FILTER:  # No subtypes for enemy
            if not has_subtype:
                bucket.elo, subtype_enemy_bucket.elo = calc_elo(bucket.elo, subtype_enemy_bucket.elo)
            else:
                bucket.elo, new_elo = calc_elo(bucket.elo, subtype_enemy_bucket.elo)
                delta_elo = new_elo - subtype_enemy_bucket.elo  # This is negative!
                # This elo will be touched twice: once in subtype, once in not-filtered type.
                # Hence take (approximately) the average delta.
                subtype_enemy_bucket.elo += round(delta_elo / 2)
        else:  # Enemy has subtypes
            enemy_bucket_key = (bucket.tour, shotdown_enemy[0], bucket.NO_FILTER)
            enemy_bucket = ensure_bucket_in_cache(cache_enemy_buckets, enemy_bucket_key)

            if has_subtype:
                if is_subtype:
                    bucket.elo, subtype_enemy_bucket.elo = calc_elo(bucket.elo, enemy_bucket.elo)
                else:
                    bucket.elo, enemy_bucket.elo = calc_elo(bucket.elo, enemy_bucket.elo)
            else:
                first_new_elo, enemy_bucket.elo = calc_elo(bucket.elo, enemy_bucket.elo)
                second_new_elo, subtype_enemy_bucket.elo = calc_elo(bucket.elo, subtype_enemy_bucket.elo)

                first_delta_elo = first_new_elo - bucket.elo
                second_delta_elo = second_new_elo - bucket.elo
                bucket.elo = round(bucket.elo + first_delta_elo / 2 + second_delta_elo / 2)

        kbs = get_killboards(shotdown_enemy, bucket, cache_kb, cache_enemy_buckets_kb)
        for kb in kbs:
            if kb.aircraft_1.aircraft == bucket.aircraft:
                kb.aircraft_1_shotdown += 1
            else:
                kb.aircraft_2_shotdown += 1
    for killed_enemy in enemies_killed:
        bucket.pilot_kills += 1
        kbs = get_killboards(killed_enemy, bucket, cache_kb, cache_enemy_buckets_kb)
        for kb in kbs:
            if kb.aircraft_1.aircraft == bucket.aircraft:
                kb.aircraft_1_kills += 1
            else:
                kb.aircraft_2_kills += 1
    return cache_enemy_buckets, cache_kb


def ensure_bucket_in_cache(cache_enemy_buckets, bucket_key):
    if bucket_key not in cache_enemy_buckets:
        cache_enemy_buckets[bucket_key] = (AircraftBucket.objects.get_or_create(
            tour=bucket_key[0], aircraft=bucket_key[1], filter_type=bucket_key[2]))[0]

    return cache_enemy_buckets[bucket_key]


def update_damaged_enemy(bucket, damaged_enemy, enemies_killed, enemies_shotdown, enemy_sortie, kb):
    if kb.aircraft_1.aircraft == bucket.aircraft:
        kb.aircraft_1_distinct_hits += 1
        bucket.distinct_enemies_hit += 1
        if enemy_sortie.is_shotdown:
            bucket.plane_lethality_counter += 1
            if damaged_enemy not in enemies_shotdown:
                kb.aircraft_1_assists += 1

        if enemy_sortie.is_dead:
            bucket.pilot_lethality_counter += 1
            if damaged_enemy not in enemies_killed:
                kb.aircraft_1_pk_assists += 1
    else:
        kb.aircraft_2_distinct_hits += 1
        bucket.distinct_enemies_hit += 1
        if enemy_sortie.is_shotdown:
            bucket.plane_lethality_counter += 1
            if damaged_enemy not in enemies_shotdown:
                kb.aircraft_2_assists += 1

        if enemy_sortie.is_dead:
            bucket.pilot_lethality_counter += 1
            if damaged_enemy not in enemies_killed:
                kb.aircraft_2_pk_assists += 1


def get_killboards(enemy, bucket, cache_kb, cache_enemy_buckets_kb):
    (enemy_aircraft, enemy_sortie) = enemy

    enemy_bucket_keys = set()
    enemy_bucket_keys.add((bucket.tour, enemy_aircraft, bucket.NO_FILTER))
    if has_bomb_variant(enemy_aircraft) or has_juiced_variant(enemy_aircraft):
        enemy_bucket_keys.add((bucket.tour, enemy_aircraft, get_sortie_type(enemy_sortie)))

    result = []
    for enemy_bucket_key in enemy_bucket_keys:
        if enemy_bucket_key in cache_enemy_buckets_kb:
            enemy_bucket = cache_enemy_buckets_kb[enemy_bucket_key]
        else:
            (enemy_bucket, created) = AircraftBucket.objects.get_or_create(
                tour=enemy_bucket_key[0], aircraft=enemy_bucket_key[1], filter_type=enemy_bucket_key[2])
            cache_enemy_buckets_kb[enemy_bucket_key] = enemy_bucket
            if created:
                enemy_bucket.update_derived_fields()
                enemy_bucket.save()

        if bucket.id < enemy_bucket.id:
            kb_key = (bucket, enemy_bucket)
        else:
            kb_key = (enemy_bucket, bucket)

        if kb_key not in cache_kb:
            kb = (AircraftKillboard.objects.get_or_create(aircraft_1=kb_key[0], aircraft_2=kb_key[1],
                                                          tour=bucket.tour))[0]
            cache_kb[kb_key] = kb
        result.append(cache_kb[kb_key])

    return result


def calc_elo(winner_rating, loser_rating):
    k = 15  # Low k factor (in chess ~30 is common), because there will be a lot of engagements.
    # k factor is the largest amount elo can shift. So a plane gains/loses at most k = 15 per engagement.
    result = expected_result(winner_rating, loser_rating)
    new_winner_rating = winner_rating + k * (1 - result)
    new_loser_rating = loser_rating + k * (0 - (1 - result))
    return int(round(new_winner_rating)), int(round(new_loser_rating))


# From https://github.com/ddm7018/Elo
def expected_result(p1, p2):
    exp = (p2 - p1) / 400.0
    return 1 / ((10.0 ** exp) + 1)


# From https://github.com/ddm7018/Elo
def is_jabo(sortie):
    allowed_exceptions = ['P-38J-25', 'Me 262 A']
    if sortie.aircraft.cls != 'aircraft_light' and sortie.aircraft.name not in allowed_exceptions:
        return False

    #             P-47                          FW-190 A-5
    jabo_mods = ['Ground attack modification', 'U17 strike modification']

    for modification in sortie.modifications:
        if 'bomb' in modification or 'rocket' in modification:
            return True
        if modification in jabo_mods:
            return True

    return False


# The P-38 and Me-262 are considered as fighters for this function.
# (They're technically aircraft_medium, i.e. attackers)
def is_juiced(sortie):
    #          P47/P51/Spit9     Tempest                               BF-109 K-4          La-5
    juices = ['150 grade fuel', 'Sabre IIA engine with +11 lb boost', 'DB 605 DC engine', 'M-82F engine',
              # Hurricane                          BF-109 G-6 Late
              'Merlin XX engine with +14 lb boost', 'MW-50 System']

    for modification in sortie.modifications:
        if modification in juices:
            return True

    return False


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


def turret_to_aircraft_bucket(turret_name, tour):
    aircraft_name = turret_name[:len(turret_name) - 7]
    if aircraft_name == 'U-2VS':
        aircraft_name = 'U-﻿2'
    aircraft = Object.objects.filter(name=aircraft_name).get()
    return (AircraftBucket.objects.get_or_create(tour=tour, aircraft=aircraft, filter_type='NO_FILTER'))[0]

# ======================== MODDED PART END

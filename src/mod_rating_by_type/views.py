from datetime import timedelta

from django.conf import settings
from django.db.models import Sum, OuterRef, Subquery, Q
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from mission_report.constants import Coalition
from stats.helpers import Paginator, get_sort_by, redirect_fix_url
from stats.models import (Player, Mission, PlayerMission, PlayerAircraft, Sortie, Tour, Profile, Squad, PlayerOnline,
                          VLife, Reward, KillboardPvP, LogEntry)
from stats.views import *
from stats.views import (_get_rating_position, _get_squad, _overall_missions_wins, _overall_stats_summary_total,
                         _overall_stats_summary_coal)

from .bullets_types import translate_ammo_breakdown, translate_damage_log_bullets
from .config_modules import *
from .models import FilteredPlayer, FilteredPlayerAircraft, FilteredVLife, FilteredReward, FilteredKillboard
from stats import sortie_log
from .turret_utils import turret_to_aircraft

INACTIVE_PLAYER_DAYS = settings.INACTIVE_PLAYER_DAYS
ITEMS_PER_PAGE = 20

missions_sort_fields = ['id', 'pilots_total', 'winning_coalition', 'duration']
squads_sort_fields = ['ak_total', 'gk_total', 'flight_time', 'kd', 'khr', 'score', 'num_members',
                      'rating_light', 'rating_medium', 'rating_heavy', 'rating']
pilots_sort_fields = ['ak_total', 'streak_current', 'gk_total', 'flight_time', 'kd', 'kl', 'khr', 'accuracy',
                      'score', 'score_light', 'score_medium', 'score_heavy', 'ak_no_ai',
                      'rating_light', 'rating_medium', 'rating_heavy', 'rating']
killboard_sort_fields = ['won', 'lose', 'wl']


def squad(request, squad_id, squad_tag=None):
    squad_ = _get_squad(request=request, squad_id=squad_id)
    if squad_.tag != squad_tag:
        return redirect_fix_url(request=request, param='squad_tag', value=squad_.tag)
    # подменяем тур на случай если выдаем другой
    request.tour = squad_.tour
    rating_position, page_position = _get_rating_position(item=squad_)
    rating_light_position, page_light_position = _get_rating_position(item=squad_, field='rating_light')
    rating_medium_position, page_medium_position = _get_rating_position(item=squad_, field='rating_medium')
    rating_heavy_position, page_heavy_position = _get_rating_position(item=squad_, field='rating_heavy')

    return render(request, 'squad.html', {
        'squad': squad_,
        'rating_position': rating_position,
        'rating_light_position': rating_light_position,
        'rating_medium_position': rating_medium_position,
        'rating_heavy_position': rating_heavy_position,
        'page_position': page_position,
        'page_light_position': page_light_position,
        'page_medium_position': page_medium_position,
        'page_heavy_position': page_heavy_position,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
    })


def squad_pilots(request, squad_id, squad_tag=None):
    squad_ = _get_squad(request=request, squad_id=squad_id)
    if squad_.tag != squad_tag:
        return redirect_fix_url(request=request, param='squad_tag', value=squad_.tag)
    # подменяем тур на случай если выдаем другой
    request.tour = squad_.tour
    sort_by = get_sort_by(request=request, sort_fields=pilots_sort_fields, default='-rating')
    pilots = Player.players.pilots(tour_id=squad_.tour_id, squad_id=squad_.id).order_by(sort_by, 'id')
    return render(request, 'squad_pilots.html', {
        'squad': squad_,
        'pilots': pilots,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
    })


def squad_rankings(request):
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()
    sort_by = get_sort_by(request=request, sort_fields=squads_sort_fields, default='-rating')
    squads = Squad.squads.filter(tour_id=request.tour.id).order_by(sort_by, 'id')
    if search:
        squads = squads.search(name=search)
    else:
        squads = squads.active()
    squads = Paginator(squads, ITEMS_PER_PAGE).page(page)
    return render(request, 'squads.html', {
        'squads': squads,
        'sort_by': sort_by,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
    })


def pilot_rankings(request):
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()
    sort_by = get_sort_by(request=request, sort_fields=pilots_sort_fields, default='-rating')
    cls = validate_and_get_player_cls(request)

    if cls == 'all':
        players = Player.players.pilots(tour_id=request.tour.id).order_by(sort_by, 'id')
        if search:
            players = players.search(name=search)
        else:
            players = players.active(tour=request.tour)
    else:
        players = FilteredPlayer.objects.filter(
            type='pilot',
            tour_id=request.tour.id,
            cls=cls
        ).order_by(sort_by, 'id')
        if search:
            players = players.filter(profile__nickname__icontains=search)
        else:
            players = __active_filter(request.tour, players)

    players = Paginator(players, ITEMS_PER_PAGE).page(page)
    return render(request, 'pilots.html', {
        'players': players,
        'sort_by': sort_by,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
        'cls': cls,
    })


def pilot(request, profile_id, nickname=None):
    tour_id = request.GET.get('tour')
    cls = validate_and_get_player_cls(request)

    player, profile = __get_player(profile_id, request, tour_id, cls, redirect_on_fail=True)
    if player is None:
        return render(request, 'pilot_not_exist.html', {'profile': profile})
    if player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=player.nickname)
    if player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'player': player})

    fav_aircraft = __get_fav_aircraft(player)

    if cls == 'all':
        rating_position, page_position = _get_rating_position(item=player)
        rating_light_position, page_light_position = _get_rating_position(item=player, field='rating_light')
        rating_medium_position, page_medium_position = _get_rating_position(item=player, field='rating_medium')
        rating_heavy_position, page_heavy_position = _get_rating_position(item=player, field='rating_heavy')
    else:
        # TODO: Make this point to the page in Filtered sorties.
        rating_position, page_position = _get_filtered_player_rating_position(player)
        rating_light_position = rating_medium_position = rating_heavy_position = None
        page_light_position = page_medium_position = page_heavy_position = None

    light_player_exists, medium_player_exists, heavy_player_exists = __find_filtered_players(profile_id, tour_id)

    return render(request, 'pilot.html', {
        'fav_aircraft': fav_aircraft,
        'player': player,
        'rating_position': rating_position,
        'rating_light_position': rating_light_position,
        'rating_medium_position': rating_medium_position,
        'rating_heavy_position': rating_heavy_position,
        'page_position': page_position,
        'page_light_position': page_light_position,
        'page_medium_position': page_medium_position,
        'page_heavy_position': page_heavy_position,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
        'light_player_exists': light_player_exists,
        'medium_player_exists': medium_player_exists,
        'heavy_player_exists': heavy_player_exists,
        'cls': cls,
    })


def __find_filtered_players(profile_id, tour_id):
    light_player_exists = FilteredPlayer.objects.filter(
        cls='light', tour_id=tour_id, profile_id=profile_id, type='pilot').exists()
    medium_player_exists = FilteredPlayer.objects.filter(
        cls='medium', tour_id=tour_id, profile_id=profile_id, type='pilot').exists()
    heavy_player_exists = FilteredPlayer.objects.filter(
        cls='heavy', tour_id=tour_id, profile_id=profile_id, type='pilot').exists()
    return light_player_exists, medium_player_exists, heavy_player_exists


def __get_player(profile_id, request, tour_id, cls='all', redirect_on_fail=False, gunner=False):
    if cls == 'all':
        player_class = Player
    else:
        player_class = FilteredPlayer

    profile = None
    if tour_id:
        try:
            query = player_class.objects.select_related('profile', 'tour')
            if cls != 'all':
                query = query.filter(cls=cls)
            if gunner:
                query = query.filter(type='gunner')
            else:
                query = query.filter(type='pilot')

            player = query.get(profile_id=profile_id, tour_id=request.tour.id)

        except player_class.DoesNotExist:
            if not redirect_on_fail:
                raise Http404

            try:
                profile = Profile.objects.get(id=profile_id)
                player = None
            except Profile.DoesNotExist:
                raise Http404

    else:
        try:
            query = (player_class.objects.select_related('profile', 'tour')
                     .filter(profile_id=profile_id, type='pilot'))
            if cls != 'all':
                query = query.filter(cls=cls)
            player = query.order_by('-id')[0]

            request.tour = player.tour
        except IndexError:
            raise Http404
    return player, profile


def __get_fav_aircraft(player):
    if isinstance(player, Player):
        aircraft_class = PlayerAircraft
    else:
        aircraft_class = FilteredPlayerAircraft
    try:
        query = (aircraft_class.objects
                 .select_related('aircraft')
                 .filter(player_id=player.id, aircraft__cls_base='aircraft'))
        if hasattr(player, 'cls'):
            query = query.filter(cls=player.cls)
        fav_aircraft = query.order_by('-sorties_total')[0]
    except IndexError:
        fav_aircraft = None
    return fav_aircraft


def __get_fav_turret_aircraft(player):
    try:
        fav_turret = (PlayerAircraft.objects
                      .select_related('aircraft')
                      .filter(player_id=player.id)
                      .order_by('-sorties_total'))[0]
    except IndexError:
        fav_turret = None

    if fav_turret is not None:
        return turret_to_aircraft(fav_turret.aircraft)
    else:
        return None


def _get_filtered_player_rating_position(filtered_player):
    if filtered_player.score == 0:
        return None, None

    position = 1 + (FilteredPlayer.objects.filter(
        tour=filtered_player.tour,
        type='pilot',
        cls=filtered_player.cls,
        rating__gt=filtered_player.rating
    ).count())
    page = (position - 1) // ITEMS_PER_PAGE + 1
    return position, page


def _get_gunner_player_rating_position(player):
    if player.score == 0:
        return None, None

    position = 1 + (Player.objects.filter(
        tour=player.tour,
        type='gunner',
        rating__gt=player.rating
    ).count())
    page = (position - 1) // ITEMS_PER_PAGE + 1
    return position, page


def pilot_sorties(request, profile_id, nickname=None):
    cls = validate_and_get_player_cls(request)

    try:
        base_player = (Player.objects.select_related('profile', 'tour')
                       .get(profile_id=profile_id, type='pilot', tour_id=request.tour.id))
        player = base_player
    except Player.DoesNotExist:
        raise Http404

    if cls != 'all':
        player, profile = __get_player(profile_id, request, base_player.tour_id, cls)

    if base_player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=base_player.nickname)
    if base_player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'base_player': base_player})
    sorties = (Sortie.objects.select_related('aircraft', 'mission')
               .filter(player_id=base_player.id)
               .exclude(status='not_takeoff')
               .order_by('-id'))
    if cls != 'all':
        sorties = sorties.filter(SortieAugmentation_MOD_SPLIT_RANKINGS__cls=cls)

    page = request.GET.get('page', 1)
    sorties = Paginator(sorties, ITEMS_PER_PAGE).page(page)
    light_player_exists, medium_player_exists, heavy_player_exists = __find_filtered_players(profile_id, player.tour_id)

    return render(request, 'pilot_sorties.html', {
        'player': player,
        'sorties': sorties,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
        'light_player_exists': light_player_exists,
        'medium_player_exists': medium_player_exists,
        'heavy_player_exists': heavy_player_exists,
        'cls': cls,
    })


def pilot_vlifes(request, profile_id, nickname=None):
    cls = validate_and_get_player_cls(request)
    player, profile = __get_player(profile_id, request, request.tour.id, cls)

    if player is None:
        return render(request, 'pilot_not_exist.html', {'profile': profile})
    if player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=player.nickname)
    if player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'player': player})
    if cls == 'all':
        vlife_class = VLife
    else:
        vlife_class = FilteredVLife

    vlifes = vlife_class.objects.filter(player_id=player.id).exclude(sorties_total=0).order_by('-id')
    if cls != 'all':
        vlifes.filter(cls=cls)

    page = request.GET.get('page', 1)
    vlifes = Paginator(vlifes, ITEMS_PER_PAGE).page(page)

    light_player_exists, medium_player_exists, heavy_player_exists = __find_filtered_players(profile_id, player.tour_id)

    return render(request, 'pilot_vlifes.html', {
        'player': player,
        'vlifes': vlifes,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
        'light_player_exists': light_player_exists,
        'medium_player_exists': medium_player_exists,
        'heavy_player_exists': heavy_player_exists,
        'cls': cls,
    })


def pilot_awards(request, profile_id, nickname=None):
    cls = validate_and_get_player_cls(request)
    player, profile = __get_player(profile_id, request, request.tour.id, cls)

    if player is None:
        return render(request, 'pilot_not_exist.html', {'profile': profile})
    if player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=player.nickname)
    if player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'player': player})

    if cls == 'all':
        reward_class = Reward
    else:
        reward_class = FilteredReward

    rewards = reward_class.objects.select_related('award').filter(player_id=player.id).order_by('award__order', '-date')
    light_player_exists, medium_player_exists, heavy_player_exists = __find_filtered_players(profile_id, player.tour_id)

    return render(request, 'pilot_awards.html', {
        'player': player,
        'rewards': rewards,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
        'light_player_exists': light_player_exists,
        'medium_player_exists': medium_player_exists,
        'heavy_player_exists': heavy_player_exists,
        'cls': cls,
    })


def pilot_killboard(request, profile_id, nickname=None):
    cls = validate_and_get_player_cls(request)
    player, profile = __get_player(profile_id, request, request.tour.id, cls)

    if player is None:
        return render(request, 'pilot_not_exist.html', {'profile': profile})
    if player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=player.nickname)
    if player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'player': player})

    if cls == 'all':
        _killboard = (KillboardPvP.objects
                      .select_related('player_1__profile', 'player_2__profile')
                      .filter(Q(player_1=player) | Q(player_2=player)))
    else:
        _killboard = (FilteredKillboard.objects
                      .select_related('player_1__profile', 'player_2__profile')
                      .filter(player_1=player))

    killboard = []
    for k in _killboard:
        if k.player_1_id == player.id:
            killboard.append({'player': k.player_2, 'won': k.won_1, 'lose': k.won_2, 'wl': k.wl_1})
        else:
            killboard.append({'player': k.player_1, 'won': k.won_2, 'lose': k.won_1, 'wl': k.wl_2})

    _sort_by = get_sort_by(request=request, sort_fields=killboard_sort_fields, default='-wl')
    sort_reverse = True if _sort_by.startswith('-') else False
    sort_by = _sort_by.replace('-', '')
    killboard = sorted(killboard, key=lambda x: x[sort_by], reverse=sort_reverse)

    light_player_exists, medium_player_exists, heavy_player_exists = __find_filtered_players(profile_id, player.tour_id)

    return render(request, 'pilot_killboard.html', {
        'player': player,
        'killboard': killboard,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
        'light_player_exists': light_player_exists,
        'medium_player_exists': medium_player_exists,
        'heavy_player_exists': heavy_player_exists,
        'cls': cls,
    })


def __top_recent_players(tour_id, by_mission, cls=None):
    if by_mission:
        return __top_last_mission_players(tour_id, cls)
    else:
        return __top_24_pilots(tour_id, cls)


def __top_last_mission_players(tour_id, cls):
    mission_query = (Mission.objects
                     .values_list('id', flat=True)
                     .filter(tour_id=tour_id, players_total__gt=0)
                     .order_by('-date_start'))

    if not mission_query.exists():
        return []

    mission_id = mission_query[0]
    score_name = 'score'
    if cls:
        score_name = 'score_' + cls

    player_missions = (PlayerMission.objects.select_related('player')
                       .filter(mission_id=mission_id, player__type='pilot')
                       .order_by('-' + score_name))[:10]

    result = []
    for player_mission in player_missions:
        result.append((player_mission.player, getattr(player_mission, score_name)))

    return result


def __top_24_pilots(tour_id, cls):
    _queryset = (Sortie.objects
                 .exclude(score=0)
                 .filter(tour_id=tour_id,
                         is_disco=False,
                         player__type='pilot',
                         profile__is_hide=False,
                         date_start__gt=timezone.now() - timedelta(hours=24)))

    if cls:
        aircraft_cls = 'aircraft_' + cls
        _queryset = _queryset.filter(
            (Q(SortieAugmentation_MOD_SPLIT_RANKINGS__cls=cls)  # Expected case. E.g. recorded jabos as type 'medium'.

             # The edge case, when this mod is freshly installed we haven't recorded type. So instead use aircraft type.
             | (Q(aircraft__cls=aircraft_cls) & Q(SortieAugmentation_MOD_SPLIT_RANKINGS=None))))

    _queryset = _queryset.values('player').annotate(sum_score=Sum('score'))
    top_24_score = _queryset.order_by('-sum_score')[:10]
    top_24_pilots = Player.players.pilots(tour_id=tour_id).filter(id__in=[s['player'] for s in top_24_score])
    top_24_pilots = {p.id: p for p in top_24_pilots}
    top_24 = []
    for p in top_24_score:
        top_24.append((top_24_pilots[p['player']], p['sum_score']))
    return top_24


def main(request):
    if request.tour.is_ended:
        return tour(request)
    missions_wins = request.tour.missions_wins()
    missions_wins_total = sum(missions_wins.values())

    summary_total = request.tour.stats_summary_total()
    summary_coal = request.tour.stats_summary_coal()

    top_streak = __top_current_streak(request.tour)
    top_24 = __top_recent_players(request.tour.id, module_active(MODULE_TOP_LAST_MISSION))

    if module_active(MODULE_SPLIT_RANKINGS):
        top_streak_heavy = __top_current_streak(request.tour, 'heavy')
        top_streak_medium = __top_current_streak(request.tour, 'medium')
        top_streak_light = __top_current_streak(request.tour, 'light')
        top_24_heavy = __top_recent_players(request.tour.id, module_active(MODULE_TOP_LAST_MISSION), cls='heavy')
        top_24_medium = __top_recent_players(request.tour.id, module_active(MODULE_TOP_LAST_MISSION), cls='medium')
        top_24_light = __top_recent_players(request.tour.id, module_active(MODULE_TOP_LAST_MISSION), cls='light')
        summary_total_heavy = request.tour.cls_stats_summary_total('heavy')
        summary_total_medium = request.tour.cls_stats_summary_total('medium')
        summary_total_light = request.tour.cls_stats_summary_total('light')
        summary_coal_heavy = request.tour.cls_stats_summary_coal('heavy')
        summary_coal_medium = request.tour.cls_stats_summary_coal('medium')
        summary_coal_light = request.tour.cls_stats_summary_coal('light')
    else:
        top_streak_heavy = None
        top_streak_medium = None
        top_streak_light = None
        top_24_heavy = None
        top_24_medium = None
        top_24_light = None
        summary_total_heavy = None
        summary_total_medium = None
        summary_total_light = None
        summary_coal_heavy = None
        summary_coal_medium = None
        summary_coal_light = None

    coal_active_players = request.tour.coal_active_players()
    total_active_players = sum(coal_active_players.values())

    try:
        previous_tour = Tour.objects.exclude(id=request.tour.id).order_by('-id')[0]
    except IndexError:
        previous_tour = None

    previous_tour_top_light = None
    previous_tour_top_medium = None
    previous_tour_top_heavy = None
    if previous_tour:
        previous_tour_top = (Player.players.pilots(tour_id=previous_tour.id)
                                 .active(tour=previous_tour).order_by('-rating')[:20])
        if module_active(MODULE_SPLIT_RANKINGS):
            previous_tour_top_light = (Player.players.pilots(tour_id=previous_tour.id)
                                           .active(tour=previous_tour).order_by('-rating_light')[:20])
            previous_tour_top_medium = (Player.players.pilots(tour_id=previous_tour.id)
                                            .active(tour=previous_tour).order_by('-rating_medium')[:20])
            previous_tour_top_heavy = (Player.players.pilots(tour_id=previous_tour.id)
                                           .active(tour=previous_tour).order_by('-rating_heavy')[:20])
    else:
        previous_tour_top = None

    coal_1_online = PlayerOnline.objects.filter(coalition=Coalition.coal_1).count()
    coal_2_online = PlayerOnline.objects.filter(coalition=Coalition.coal_2).count()
    total_online = coal_1_online + coal_2_online

    return render(request, 'main.html', {
        'tour': request.tour,
        'missions_wins': missions_wins,
        'missions_wins_total': missions_wins_total,
        'summary_total': summary_total,
        'summary_coal': summary_coal,
        'summary_total_heavy': summary_total_heavy,
        'summary_total_medium': summary_total_medium,
        'summary_total_light': summary_total_light,
        'summary_coal_heavy': summary_coal_heavy,
        'summary_coal_medium': summary_coal_medium,
        'summary_coal_light': summary_coal_light,
        'top_streak': top_streak,
        'top_streak_heavy': top_streak_heavy,
        'top_streak_medium': top_streak_medium,
        'top_streak_light': top_streak_light,
        'top_24': top_24,
        'top_24_heavy': top_24_heavy,
        'top_24_medium': top_24_medium,
        'top_24_light': top_24_light,
        'coal_active_players': coal_active_players,
        'total_active_players': total_active_players,
        'previous_tour': previous_tour,
        'previous_tour_top': previous_tour_top,
        'previous_tour_top_light': previous_tour_top_light,
        'previous_tour_top_medium': previous_tour_top_medium,
        'previous_tour_top_heavy': previous_tour_top_heavy,
        'total_online': total_online,
        'coal_1_online': coal_1_online,
        'coal_2_online': coal_2_online,
        'MODULE_TOP_LAST_MISSION': module_active(MODULE_TOP_LAST_MISSION),
    })


def __top_current_streak(tour, cls='all'):
    field = 'score_streak_current'
    if cls != 'all':
        field += '_' + cls
    sort_by = '-' + field

    if cls != 'all' and FilteredPlayer.objects.filter(tour=tour).exists():
        query = (FilteredPlayer.objects.filter(tour_id=tour.id, type='pilot', cls=cls)
                 .exclude(**{field: 0}))
        query = __active_filter(tour, query).order_by(sort_by)
        return query[:10]

    else:
        return (Player.players.pilots(tour_id=tour.id)
                    .exclude(score_streak_current=0)
                    .active(tour=tour).order_by(sort_by)[:10])


def __active_filter(tour, query):
    if settings.INACTIVE_PLAYER_DAYS:
        if tour.is_ended:
            date = tour.date_end - settings.INACTIVE_PLAYER_DAYS
        else:
            date = timezone.now() - settings.INACTIVE_PLAYER_DAYS
        return query.filter(date_last_combat__gt=date, tour_id=tour.id)
    else:
        return query.filter(tour_id=tour.id)


def tour(request):
    missions_wins = request.tour.missions_wins()
    missions_wins_total = sum(missions_wins.values())

    summary_total = request.tour.stats_summary_total()
    summary_coal = request.tour.stats_summary_coal()

    top_streak = __top_max_streak(request.tour)

    top_rating = (Player.players.pilots(tour_id=request.tour.id)
                      .exclude(rating=0)
                      .active(tour=request.tour).order_by('-rating')[:10])

    if module_active(MODULE_SPLIT_RANKINGS):
        top_rating_heavy = (Player.players.pilots(tour_id=request.tour.id)
                                .exclude(rating_heavy=0)
                                .active(tour=request.tour).order_by('-rating_heavy')[:10])

        top_rating_medium = (Player.players.pilots(tour_id=request.tour.id)
                                 .exclude(rating_medium=0)
                                 .active(tour=request.tour).order_by('-rating_medium')[:10])

        top_rating_light = (Player.players.pilots(tour_id=request.tour.id)
                                .exclude(rating_light=0)
                                .active(tour=request.tour).order_by('-rating_light')[:10])
        top_streak_heavy = __top_max_streak(request.tour, cls='heavy')
        top_streak_medium = __top_max_streak(request.tour, cls='medium')
        top_streak_light = __top_max_streak(request.tour, cls='light')
    else:
        top_rating_heavy = None
        top_rating_medium = None
        top_rating_light = None
        top_streak_heavy = None
        top_streak_medium = None
        top_streak_light = None

    coal_active_players = request.tour.coal_active_players()
    total_active_players = sum(coal_active_players.values())

    return render(request, 'tour.html', {
        'tour': request.tour,
        'missions_wins': missions_wins,
        'missions_wins_total': missions_wins_total,
        'summary_total': summary_total,
        'summary_coal': summary_coal,
        'top_streak': top_streak,
        'top_streak_heavy': top_streak_heavy,
        'top_streak_medium': top_streak_medium,
        'top_streak_light': top_streak_light,
        'top_rating': top_rating,
        'top_rating_heavy': top_rating_heavy,
        'top_rating_medium': top_rating_medium,
        'top_rating_light': top_rating_light,
        'coal_active_players': coal_active_players,
        'total_active_players': total_active_players,
    })


def __top_max_streak(tour, cls='all'):
    field = 'score_streak_max'
    if cls != 'all':
        field += '_' + cls
    sort_by = '-' + field

    if cls != 'all' and FilteredPlayer.objects.filter(tour=tour).exists():

        query = (FilteredPlayer.objects.filter(tour_id=tour.id, type='pilot', cls=cls)
                 .exclude(**{field: 0}))
        query = __active_filter(tour, query).order_by(sort_by)
        return query[:10]

    else:
        return (Player.players.pilots(tour_id=tour.id)
                    .exclude(score_streak_max=0)
                    .active(tour=tour).order_by(sort_by)[:10])


def mission(request, mission_id):
    mission_ = get_object_or_404(Mission, id=mission_id)
    sort_by = request.GET.get('sort_by', '-score')
    if sort_by.replace('-', '') not in pilots_sort_fields:
        return redirect('stats:players_list', permanent=False)
    players = (PlayerMission.objects.select_related('player', 'profile')
               .filter(mission_id=mission_id, player__type='pilot')
               # .only('profile_id', 'player__tour_id', 'ak_total', 'gk_total', 'flight_time',
               #       'kd', 'khr', 'accuracy', 'score', 'sorties_coal', 'sorties_total')
               .order_by(sort_by, '-flight_time'))

    summary_total = mission_.stats_summary_total()
    summary_coal = mission_.stats_summary_coal()

    return render(request, 'mission.html', {
        'mission': mission_,
        'players': players,
        'sort_by': sort_by,
        'summary_total': summary_total,
        'summary_coal': summary_coal,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
    })


def pilot_sortie(request, sortie_id):
    try:
        sortie = (Sortie.objects
                  .select_related('player', 'player__profile', 'player__tour', 'mission')
                  .get(id=sortie_id, player__type='pilot'))
    except Sortie.DoesNotExist:
        raise Http404

    # обработка старого формат хранения очков, без AI очков
    mission_score_dict = {}
    for k, v in sortie.mission.score_dict.items():
        if isinstance(v, dict):
            break
        mission_score_dict[k] = {'base': v, 'ai': v}

    if 'ammo_breakdown' in sortie.ammo and module_active(MODULE_AMMO_BREAKDOWN):
        ammo_breakdown = translate_ammo_breakdown(sortie.ammo['ammo_breakdown'])
    else:
        ammo_breakdown = dict()

    if 'penalty_pct' in sortie.score_dict:
        base_score = sortie.score_dict['basic']
        penalty_pct = sortie.score_dict['penalty_pct']
        sortie.score_dict['after_penalty_score'] = int(base_score * ((100 - penalty_pct) / 100))

    return render(request, 'pilot_sortie.html', {
        'player': sortie.player,
        'sortie': sortie,
        'score_dict': mission_score_dict or sortie.mission.score_dict,
        'ammo_breakdown': ammo_breakdown,
        'ammo_breakdown_module': module_active(MODULE_AMMO_BREAKDOWN),
    })


def pilot_sortie_log(request, sortie_id):
    try:
        sortie = Sortie.objects.select_related('player', 'player__profile', 'player__tour', 'mission').get(id=sortie_id)
    except Sortie.DoesNotExist:
        raise Http404
    events = (LogEntry.objects
              .select_related('act_object', 'act_sortie', 'cact_object', 'cact_sortie')
              .filter(Q(act_sortie_id=sortie.id) | Q(cact_sortie_id=sortie.id))
              .exclude(
        Q(act_object__cls='trash') | Q(cact_object__cls='trash') | Q(type='shotdown', act_object__isnull=True))
              .order_by('tik'))
    for e in events:
        is_friendly_fire = e.extra_data.get('is_friendly_fire', False)
        if e.cact_sortie and e.cact_sortie.id == sortie.id:
            e.message = sortie_log.get_message(act_type='cact', event_type=e.type, has_opponent=e.act_object)
            e.color = sortie_log.get_color(act_type='cact', event_type=e.type, is_friendly_fire=is_friendly_fire)
            e.opponent_sortie = e.act_sortie
            e.opponent_object = e.act_object
            e.opponent_act = True
        elif e.act_sortie and e.act_sortie.id == sortie.id:
            e.message = sortie_log.get_message(act_type='act', event_type=e.type, has_opponent=e.cact_object)
            e.color = sortie_log.get_color(act_type='act', event_type=e.type, is_friendly_fire=is_friendly_fire)
            e.opponent_sortie = e.cact_sortie
            e.opponent_object = e.cact_object
            e.opponent_act = False

        if ((e.type == 'damaged' or e.type == 'wounded') and type(e.extra_data['damage']) is dict
                and 'hits' in e.extra_data['damage']):
            e.extra_data['damage']['translated_hits'] = translate_damage_log_bullets(e.extra_data['damage']['hits'])

    return render(request, 'pilot_sortie_log.html', {
        'player': sortie.player,
        'sortie': sortie,
        'events': events,
        'MODULE_AMMO_BREAKDOWN': module_active(MODULE_AMMO_BREAKDOWN),
    })


def ironman_stats(request):
    if not module_active(MODULE_IRONMAN_STATS):
        raise Http404("Ironman stats not available on this server.")
    cls = validate_and_get_player_cls(request)

    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()
    sort_by = get_sort_by(request=request, sort_fields=pilots_sort_fields, default='-score')

    if cls == 'all':
        vlife_object = VLife
        if sort_by == 'ak_no_ai':
            sort_by = 'VLifeAugmentation_MOD_SPLIT_RANKINGS__ak_no_ai'
        if sort_by == '-ak_no_ai':
            sort_by = '-VLifeAugmentation_MOD_SPLIT_RANKINGS__ak_no_ai'
    else:
        vlife_object = FilteredVLife

    players = (vlife_object.objects
               .filter(tour__id=request.tour.id, sorties_total__gt=0, player__type='pilot')
               .exclude(profile__is_hide=True)
               .order_by(sort_by, 'id'))
    if cls != 'all':
        players = players.filter(cls=cls)

    if not request.tour.is_ended:
        players.filter(relive=0)

    if search:
        players = players.filter(player__profile__nickname__icontains=search)

    players = Paginator(players, ITEMS_PER_PAGE).page(page)
    return render(request, 'ironman_pilots.html', {
        'players': players,
        'sort_by': sort_by,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
        'no_ai_streaks': module_active(MODULE_AIR_STREAKS_NO_AI),
        'cls': cls,
    })


def pilot_vlife(request, vlife_id):
    cls = validate_and_get_player_cls(request)

    if cls == 'all':
        vlife_class = VLife
    else:
        vlife_class = FilteredVLife

    try:
        vlife = (vlife_class.objects
                 .select_related('player', 'player__profile', 'player__tour')
                 .get(id=vlife_id, player__type='pilot'))

    except VLife.DoesNotExist:
        raise Http404
    return render(request, 'pilot_vlife.html', {
        'player': vlife.player,
        'vlife': vlife,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
        'ironman_stats:': module_active(MODULE_IRONMAN_STATS),
        'cls': cls,
    })


def overall(request):
    missions_wins = _overall_missions_wins()
    missions_wins_total = sum(missions_wins.values())
    summary_total = _overall_stats_summary_total()
    summary_coal = _overall_stats_summary_coal()

    top_rating = (Player.players.pilots()
                      .exclude(rating=0)
                      .order_by('-rating')[:10])

    top_streak_score = (Player.players.pilots()
                            .exclude(score_streak_max=0)
                            .order_by('-score_streak_max')[:10])

    top_streak_ak = (Player.players.pilots()
                         .exclude(streak_max=0)
                         .order_by('-streak_max')[:10])

    top_streak_gk = (Player.players.pilots()
                         .exclude(streak_ground_max=0)
                         .order_by('-streak_ground_max')[:10])

    total_players = Profile.objects.count()

    if module_active(MODULE_SPLIT_RANKINGS):
        top_rating_light = _top_rating('light')
        top_rating_medium = _top_rating('medium')
        top_rating_heavy = _top_rating('heavy')

        top_streak_ak_light = FilteredPlayer.objects.filter(
            type='pilot', cls='light'
        ).exclude(streak_max=0).order_by('-streak_max')[:10]
        top_streak_gk_medium = FilteredPlayer.objects.filter(
            type='pilot', cls='medium'
        ).exclude(streak_ground_max=0).order_by('-streak_ground_max')[:10]
        top_streak_gk_heavy = FilteredPlayer.objects.filter(
            type='pilot', cls='heavy'
        ).exclude(streak_ground_max=0).order_by('-streak_ground_max')[:10]
    else:
        top_rating_light = top_rating_medium = top_rating_heavy = None
        top_streak_ak_light = top_streak_gk_medium = top_streak_gk_heavy = None

    return render(request, 'overall.html', {
        'tour': request.tour,
        'missions_wins': missions_wins,
        'missions_wins_total': missions_wins_total,
        'summary_total': summary_total,
        'summary_coal': summary_coal,
        'top_rating': top_rating,
        'top_streak_score': top_streak_score,
        'top_streak_ak': top_streak_ak,
        'top_streak_gk': top_streak_gk,
        'total_players': total_players,
        'top_rating_light': top_rating_light,
        'top_rating_medium': top_rating_medium,
        'top_rating_heavy': top_rating_heavy,
        'top_streak_ak_light': top_streak_ak_light,
        'top_streak_gk_medium': top_streak_gk_medium,
        'top_streak_gk_heavy': top_streak_gk_heavy,
    })


def _top_rating(cls):
    return FilteredPlayer.objects.filter(
        type='pilot', cls=cls,
    ).exclude(rating=0).order_by('-rating')[:10]


def validate_and_get_player_cls(request):
    cls = request.GET.get('cls', 'all')
    if cls != 'all' and not module_active(MODULE_SPLIT_RANKINGS):
        raise Http404("Server does not have split rankings.")
    if cls not in {'all', 'heavy', 'medium', 'light'}:
        raise Http404("Invalid cls")
    return cls


def gunner_sortie(request, sortie_id):
    if not module_active(MODULE_GUNNER_STATS):
        raise Http404("Gunner stats not available on this server.")

    try:
        sortie = (Sortie.objects
                  .select_related('player', 'player__profile', 'player__tour', 'mission')
                  .get(id=sortie_id, player__type='gunner'))
    except Sortie.DoesNotExist:
        raise Http404

    # обработка старого формат хранения очков, без AI очков
    mission_score_dict = {}
    for k, v in sortie.mission.score_dict.items():
        if isinstance(v, dict):
            break
        mission_score_dict[k] = {'base': v, 'ai': v}

    if 'penalty_pct' in sortie.score_dict:
        base_score = sortie.score_dict['basic']
        penalty_pct = sortie.score_dict['penalty_pct']
        sortie.score_dict['after_penalty_score'] = int(base_score * ((100 - penalty_pct) / 100))

    if 'ammo_breakdown' in sortie.ammo and module_active(MODULE_AMMO_BREAKDOWN):
        ammo_breakdown = translate_ammo_breakdown(sortie.ammo['ammo_breakdown'])
    else:
        ammo_breakdown = dict()

    aircraft = turret_to_aircraft(sortie.aircraft)

    return render(request, 'gunner_sortie.html', {
        'player': sortie.player,
        'sortie': sortie,
        'score_dict': mission_score_dict or sortie.mission.score_dict,
        'ammo_breakdown': ammo_breakdown,
        'ammo_breakdown_module': module_active(MODULE_AMMO_BREAKDOWN),
        'aircraft': aircraft,
    })


def gunner_vlifes(request, profile_id, nickname=None):
    if not module_active(MODULE_GUNNER_STATS):
        raise Http404("Gunner stats not available on this server.")

    player, profile = __get_player(profile_id, request, request.tour.id, gunner=True)

    if player is None:
        return render(request, 'pilot_not_exist.html', {'profile': profile})
    if player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=player.nickname)
    if player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'player': player})

    vlifes = VLife.objects.filter(player_id=player.id).exclude(sorties_total=0).order_by('-id')

    page = request.GET.get('page', 1)
    vlifes = Paginator(vlifes, ITEMS_PER_PAGE).page(page)

    return render(request, 'gunner_vlifes.html', {
        'player': player,
        'vlifes': vlifes,
    })


def gunner_vlife(request, vlife_id):
    if not module_active(MODULE_GUNNER_STATS):
        raise Http404("Gunner stats not available on this server.")

    try:
        vlife = (VLife.objects
                 .select_related('player', 'player__profile', 'player__tour')
                 .get(id=vlife_id, player__type='gunner'))

    except VLife.DoesNotExist:
        raise Http404
    return render(request, 'gunner_vlife.html', {
        'player': vlife.player,
        'vlife': vlife,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
    })


def gunner_sortie_log(request, sortie_id):
    if not module_active(MODULE_GUNNER_STATS):
        raise Http404("Gunner stats not available on this server.")

    try:
        sortie = Sortie.objects.select_related('player', 'player__profile', 'player__tour', 'mission').get(id=sortie_id)
    except Sortie.DoesNotExist:
        raise Http404
    events = (LogEntry.objects
              .select_related('act_object', 'act_sortie', 'cact_object', 'cact_sortie')
              .filter(Q(act_sortie_id=sortie.id) | Q(cact_sortie_id=sortie.id))
              .exclude(
        Q(act_object__cls='trash') | Q(cact_object__cls='trash') | Q(type='shotdown', act_object__isnull=True))
              .order_by('tik'))
    for e in events:
        is_friendly_fire = e.extra_data.get('is_friendly_fire', False)
        if e.cact_sortie and e.cact_sortie.id == sortie.id:
            e.message = sortie_log.get_message(act_type='cact', event_type=e.type, has_opponent=e.act_object)
            e.color = sortie_log.get_color(act_type='cact', event_type=e.type, is_friendly_fire=is_friendly_fire)
            e.opponent_sortie = e.act_sortie
            e.opponent_object = e.act_object
            e.opponent_act = True
        elif e.act_sortie and e.act_sortie.id == sortie.id:
            e.message = sortie_log.get_message(act_type='act', event_type=e.type, has_opponent=e.cact_object)
            e.color = sortie_log.get_color(act_type='act', event_type=e.type, is_friendly_fire=is_friendly_fire)
            e.opponent_sortie = e.cact_sortie
            e.opponent_object = e.cact_object
            e.opponent_act = False

        if ((e.type == 'damaged' or e.type == 'wounded') and type(e.extra_data['damage']) is dict
                and 'hits' in e.extra_data['damage']):
            e.extra_data['damage']['translated_hits'] = translate_damage_log_bullets(e.extra_data['damage']['hits'])

    return render(request, 'gunner_sortie_log.html', {
        'player': sortie.player,
        'sortie': sortie,
        'events': events,
        'MODULE_AMMO_BREAKDOWN': module_active(MODULE_AMMO_BREAKDOWN),
    })


def gunner_killboard(request, profile_id, nickname=None):
    if not module_active(MODULE_GUNNER_STATS):
        raise Http404("Gunner stats not available on this server.")

    player, profile = __get_player(profile_id, request, request.tour.id, gunner=True)

    if player is None:
        return render(request, 'pilot_not_exist.html', {'profile': profile})
    if player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=player.nickname)
    if player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'player': player})

    _killboard = (KillboardPvP.objects
                  .select_related('player_1__profile', 'player_2__profile')
                  .filter(Q(player_1=player) | Q(player_2=player)))

    killboard = []
    for k in _killboard:
        if k.player_1_id == player.id:
            killboard.append({'player': k.player_2, 'won': k.won_1, 'lose': k.won_2, 'wl': k.wl_1})
        else:
            killboard.append({'player': k.player_1, 'won': k.won_2, 'lose': k.won_1, 'wl': k.wl_2})

    _sort_by = get_sort_by(request=request, sort_fields=killboard_sort_fields, default='-wl')
    sort_reverse = True if _sort_by.startswith('-') else False
    sort_by = _sort_by.replace('-', '')
    killboard = sorted(killboard, key=lambda x: x[sort_by], reverse=sort_reverse)

    return render(request, 'gunner_killboard.html', {
        'player': player,
        'killboard': killboard,
    })


def gunner_awards(request, profile_id, nickname=None):
    if not module_active(MODULE_GUNNER_STATS):
        raise Http404("Gunner stats not available on this server.")

    player, profile = __get_player(profile_id, request, request.tour.id, gunner=True)

    if player is None:
        return render(request, 'pilot_not_exist.html', {'profile': profile})
    if player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=player.nickname)
    if player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'player': player})

    rewards = Reward.objects.select_related('award').filter(player_id=player.id).order_by('award__order', '-date')

    return render(request, 'gunner_awards.html', {
        'player': player,
        'rewards': rewards,
    })


def gunner_sorties(request, profile_id, nickname=None):
    # Fix it.
    if not module_active(MODULE_GUNNER_STATS):
        raise Http404("Gunner stats not available on this server.")

    try:
        base_player = (Player.objects.select_related('profile', 'tour')
                       .get(profile_id=profile_id, type='gunner', tour_id=request.tour.id))
        player = base_player
    except Player.DoesNotExist:
        raise Http404

    if base_player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=base_player.nickname)
    if base_player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'base_player': base_player})
    sorties = (Sortie.objects.select_related('aircraft', 'mission')
               .filter(player_id=base_player.id)
               .order_by('-id'))

    page = request.GET.get('page', 1)
    sorties = Paginator(sorties, ITEMS_PER_PAGE).page(page)

    return render(request, 'gunner_sorties.html', {
        'player': player,
        'sorties': sorties,
    })


def gunners(request):
    if not module_active(MODULE_GUNNER_STATS):
        raise Http404("Gunner stats not available on this server.")

    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()
    sort_by = get_sort_by(request=request, sort_fields=pilots_sort_fields, default='-rating')

    players = Player.objects.filter(
        type='gunner',
        tour_id=request.tour.id
    ).order_by(sort_by)
    if search:
        players = players.filter(profile__nickname__icontains=search)
    else:
        players = __active_filter(request.tour, players)

    players = Paginator(players, ITEMS_PER_PAGE).page(page)
    return render(request, 'gunners.html', {
        'players': players,
        'sort_by': sort_by,
    })


def gunner(request, profile_id, nickname=None):
    if not module_active(MODULE_GUNNER_STATS):
        raise Http404("Gunner stats not available on this server.")

    tour_id = request.GET.get('tour')

    player, profile = __get_player(profile_id, request, tour_id, gunner=True)
    if player is None:
        return render(request, 'pilot_not_exist.html', {'profile': profile})
    if player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=player.nickname)
    if player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'player': player})

    rating_position, page_position = _get_gunner_player_rating_position(player)
    fav_aircraft = __get_fav_turret_aircraft(player)

    return render(request, 'gunner.html', {
        'fav_aircraft': fav_aircraft,
        'player': player,
        'rating_position': rating_position,
        'page_position': page_position,
    })

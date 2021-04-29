from datetime import timedelta

from django.conf import settings
from django.db.models import Sum, OuterRef, Subquery, Q
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from mission_report.constants import Coalition
from stats.helpers import Paginator, get_sort_by, redirect_fix_url
from stats.models import (Player, Mission, PlayerMission, PlayerAircraft, Sortie, Tour, Profile, Squad, PlayerOnline,
                          VLife)
from stats.views import *
from stats.views import _get_rating_position, _get_squad

from .bullets_types import translate_ammo_breakdown
from .config_modules import *
from .variant_utils import FIGHTER_WHITE_LIST

INACTIVE_PLAYER_DAYS = settings.INACTIVE_PLAYER_DAYS
ITEMS_PER_PAGE = 20


missions_sort_fields = ['id', 'players_total', 'pilots_total', 'tankmans_total', 'winning_coalition', 'duration']
squads_sort_fields = ['ak_total', 'gk_total', 'flight_time', 'kd', 'khr', 'score', 'num_members',
                      'rating_light', 'rating_medium', 'rating_heavy', 'rating']
pilots_sort_fields = ['ak_total', 'streak_current', 'gk_total', 'flight_time', 'kd', 'kl', 'khr', 'accuracy', 'gkd',
                      'gkhr','score', 'score_light', 'score_medium', 'score_heavy',
                      'rating_light', 'rating_medium', 'rating_heavy', 'rating']
tankmans_sort_fields = ['gk_total', 'streak_ground_current', 'ak_total', 'flight_time', 'kd', 'khr', 'gkd', 'gkhr', 'accuracy', 'score', 'rating']
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
    players = Player.players.pilots(tour_id=request.tour.id).order_by(sort_by, 'id')
    if search:
        players = players.search(name=search)
    else:
        players = players.active(tour=request.tour)
    players = Paginator(players, ITEMS_PER_PAGE).page(page)
    return render(request, 'pilots.html', {
        'players': players,
        'sort_by': sort_by,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
    })


def pilot(request, profile_id, nickname=None):
    tour_id = request.GET.get('tour')
    if tour_id:
        try:
            player = (Player.objects.select_related('profile', 'tour')
                      .get(profile_id=profile_id, type='pilot', tour_id=request.tour.id))
        except Player.DoesNotExist:
            try:
                profile = Profile.objects.get(id=profile_id)
                return render(request, 'pilot_not_exist.html', {'profile': profile})
            except Profile.DoesNotExist:
                raise Http404
    else:
        try:
            player = (Player.objects.select_related('profile', 'tour')
                .filter(profile_id=profile_id, type='pilot').order_by('-id')[0])
            request.tour = player.tour
        except IndexError:
            try:
                player = (Player.objects.select_related('profile', 'tour')
                    .filter(profile_id=profile_id, type='tankman').order_by('-id')[0])
                request.tour = player.tour
            except Profile.DoesNotExist:
                raise Http404

    if player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=player.nickname)
    if player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'player': player})

    try:
        fav_aircraft = (PlayerAircraft.objects
            .select_related('aircraft')
            .filter(player_id=player.id, aircraft__cls_base='aircraft')
            .order_by('-sorties_total')[0])
    except IndexError:
        fav_aircraft = None

    rating_position, page_position = _get_rating_position(item=player)
    rating_light_position, page_light_position = _get_rating_position(item=player, field='rating_light')
    rating_medium_position, page_medium_position = _get_rating_position(item=player, field='rating_medium')
    rating_heavy_position, page_heavy_position = _get_rating_position(item=player, field='rating_heavy')

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
    })


def __top_24_pilots(tour_id, cls=None):
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
            (Q(SortieAugmentation_MOD_SPLIT_RANKINGS__cls=cls) # Expected case. E.g. recorded jabos as type 'medium'.

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

    top_streak = (Player.players.pilots(tour_id=request.tour.id)
                      .exclude(score_streak_current=0)
                      .active(tour=request.tour).order_by('-score_streak_current')[:10])

    top_24 = __top_24_pilots(tour_id=request.tour.id)

    if module_active(MODULE_SPLIT_RANKINGS):
        top_streak_heavy = (Player.players.pilots(tour_id=request.tour.id)
                                .exclude(score_streak_current_heavy=0)
                                .active(tour=request.tour).order_by('-score_streak_current_heavy')[:10])
        top_streak_medium = (Player.players.pilots(tour_id=request.tour.id)
                                 .exclude(score_streak_current_medium=0)
                                 .active(tour=request.tour).order_by('-score_streak_current_medium')[:10])
        top_streak_light = (Player.players.pilots(tour_id=request.tour.id)
                                .exclude(score_streak_current_light=0)
                                .active(tour=request.tour).order_by('-score_streak_current_light')[:10])
        top_24_heavy = __top_24_pilots(tour_id=request.tour.id, cls='heavy')
        top_24_medium = __top_24_pilots(tour_id=request.tour.id, cls='medium')
        top_24_light = __top_24_pilots(tour_id=request.tour.id, cls='light')
    else:
        top_streak_heavy = None
        top_streak_medium = None
        top_streak_light = None
        top_24_heavy = None
        top_24_medium = None
        top_24_light = None

    toptank_streak = (Player.players.tankmans(tour_id=request.tour.id)
                          .exclude(score_streak_current=0)
                          .active(tour=request.tour).order_by('-score_streak_current')[:10])
    toptank_24_score = (Sortie.objects
                            .filter(tour_id=request.tour.id, is_disco=False, player__type='tankman',
                                    profile__is_hide=False)
                            .filter(date_start__gt=timezone.now() - timedelta(hours=24))
                            .exclude(score=0)
                            .values('player')
                            .annotate(sum_score=Sum('score'))
                            .order_by('-sum_score')[:10])
    toptank_24_tankmans = (Player.players.tankmans(tour_id=request.tour.id)
                           .filter(id__in=[s['player'] for s in toptank_24_score]))
    toptank_24_tankmans = {p.id: p for p in toptank_24_tankmans}
    toptank_24 = []
    for p in toptank_24_score:
        toptank_24.append((toptank_24_tankmans[p['player']], p['sum_score']))

    coal_active_tankmans = request.tour.coal_active_tankmans()
    total_active_tankmans = sum(coal_active_tankmans.values())

    coal_active_pilots = request.tour.coal_active_pilots()
    total_active_pilots = sum(coal_active_pilots.values())

    try:
        previous_tour = Tour.objects.exclude(id=request.tour.id).order_by('-id')[0]
    except IndexError:
        previous_tour = None

    previous_tour_top_light = None
    previous_tour_top_medium = None
    previous_tour_top_heavy = None
    previous_tour_toptank = None
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
            previous_tour_toptank = (Player.players.tankmans(tour_id=previous_tour.id)
                                         .active(tour=previous_tour).order_by('-rating')[:20])
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
        'top_streak': top_streak,
        'toptank_streak': toptank_streak,
        'top_streak_heavy': top_streak_heavy,
        'top_streak_medium': top_streak_medium,
        'top_streak_light': top_streak_light,
        'top_24': top_24,
        'toptank_24': toptank_24,
        'top_24_heavy': top_24_heavy,
        'top_24_medium': top_24_medium,
        'top_24_light': top_24_light,
        'coal_active_pilots': coal_active_pilots,
        'coal_active_tankmans': coal_active_tankmans,
        'total_active_pilots': total_active_pilots,
        'total_active_tankmans': total_active_tankmans,
        'previous_tour': previous_tour,
        'previous_tour_top': previous_tour_top,
        'previous_tour_top_light': previous_tour_top_light,
        'previous_tour_top_medium': previous_tour_top_medium,
        'previous_tour_top_heavy': previous_tour_top_heavy,
        'previous_tour_toptank': previous_tour_toptank,
        'total_online': total_online,
        'coal_1_online': coal_1_online,
        'coal_2_online': coal_2_online,
    })


def tour(request):
    missions_wins = request.tour.missions_wins()
    missions_wins_total = sum(missions_wins.values())

    summary_total = request.tour.stats_summary_total()
    summary_coal = request.tour.stats_summary_coal()

    top_streak = (Player.players.pilots(tour_id=request.tour.id)
                      .exclude(score_streak_max=0)
                      .active(tour=request.tour).order_by('-score_streak_max')[:10])

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

        top_streak_heavy = (Player.players.pilots(tour_id=request.tour.id)
                                .exclude(score_streak_max_heavy=0)
                                .active(tour=request.tour).order_by('-score_streak_max_heavy')[:10])

        top_streak_medium = (Player.players.pilots(tour_id=request.tour.id)
                                 .exclude(score_streak_max_medium=0)
                                 .active(tour=request.tour).order_by('-score_streak_max_medium')[:10])

        top_streak_light = (Player.players.pilots(tour_id=request.tour.id)
                                .exclude(score_streak_max_light=0)
                                .active(tour=request.tour).order_by('-score_streak_max_light')[:10])
    else:
        top_rating_heavy = None
        top_rating_medium = None
        top_rating_light = None
        top_streak_heavy = None
        top_streak_medium = None
        top_streak_light = None

    coal_active_pilots = request.tour.coal_active_pilots()
    total_active_pilots = sum(coal_active_pilots.values())

    toptank_streak = (Player.players.tankmans(tour_id=request.tour.id)
                  .exclude(score_streak_max=0)
                  .active(tour=request.tour).order_by('-score_streak_max')[:10])
    toptank_rating = (Player.players.tankmans(tour_id=request.tour.id)
                  .exclude(rating=0)
                  .active(tour=request.tour).order_by('-rating')[:10])

    coal_active_tankmans = request.tour.coal_active_tankmans()
    total_active_tankmans = sum(coal_active_tankmans.values())

    return render(request, 'tour.html', {
        'tour': request.tour,
        'missions_wins': missions_wins,
        'missions_wins_total': missions_wins_total,
        'summary_total': summary_total,
        'summary_coal': summary_coal,
        'top_streak': top_streak,
        'toptank_streak': toptank_streak,
        'top_streak_heavy': top_streak_heavy,
        'top_streak_medium': top_streak_medium,
        'top_streak_light': top_streak_light,
        'top_rating': top_rating,
        'toptank_rating': toptank_rating,
        'top_rating_heavy': top_rating_heavy,
        'top_rating_medium': top_rating_medium,
        'top_rating_light': top_rating_light,
        'coal_active_pilots': coal_active_pilots,
        'total_active_pilots': total_active_pilots,
        'coal_active_tankmans': coal_active_tankmans,
        'total_active_tankmans': total_active_tankmans,
    })


def mission(request, mission_id):
    mission_ = get_object_or_404(Mission, id=mission_id)
    sort_by = request.GET.get('sort_by', '-score')
    if sort_by.replace('-', '') not in pilots_sort_fields:
        return redirect('stats:players_list', permanent=False)
    pilots = (PlayerMission.objects.select_related('player', 'profile')
               .filter(mission_id=mission_id, player__type='pilot')
               # .only('profile_id', 'player__tour_id', 'ak_total', 'gk_total', 'flight_time',
               #       'kd', 'khr', 'accuracy', 'score', 'sorties_coal', 'sorties_total')
               .order_by(sort_by, '-flight_time'))

    tankmans = (PlayerMission.objects.select_related('player', 'profile')
                .filter(mission_id=mission_id, player__type='tankman')
                # .only('profile_id', 'player__tour_id', 'ak_total', 'gk_total', 'flight_time',
                #       'gkd', 'gkhr', 'kd', 'khr', 'accuracy', 'score', 'sorties_coal', 'sorties_total')
                .order_by(sort_by, '-flight_time'))

    summary_total = mission_.stats_summary_total()
    summary_coal = mission_.stats_summary_coal()

    return render(request, 'mission.html', {
        'mission': mission_,
        'pilots': pilots,
        'tankmans': tankmans,
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
    })


def ironman_stats(request):
    if not module_active(MODULE_IRONMAN_STATS):
        raise Http404("Ironman stats not available on this server.")

    request.tour.is_ended = True

    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()
    sort_by = get_sort_by(request=request, sort_fields=pilots_sort_fields, default='-score')
    if request.tour.is_ended:
        to_max = '-score'
        if 'score_light' in sort_by:
            to_max = '-score_light'
        if 'score_medium' in sort_by:
            to_max = '-score_medium'
        if 'score_heavy' in sort_by:
            to_max = '-score_heavy'

        players = get_best_streak_ironman(request.tour.id, to_max).order_by(sort_by, 'id')
    else:
        players = (VLife.objects
                   .filter(relive=0, tour_id=request.tour.id, sorties_total__gt=0, player__type='pilot')
                   .exclude(profile__is_hide=True)
                   .order_by(sort_by, 'id'))

    if search:
        players = players.filter(player__profile__nickname__icontains=search)

    players = Paginator(players, ITEMS_PER_PAGE).page(page)
    return render(request, 'ironman_pilots.html', {
        'players': players,
        'sort_by': sort_by,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
    })


# Basically, the following (psuedo code) SQL is wanted:
#   SELECT *, Max(score)
#   FROM VLife
#   WHERE tour.id = tour_id AND sorties_total > 0 AND player_type = 'pilot' AND NOT profile.is.hide
#   GROUP BY player.profile.id
#
# Where we want to extract VLife objects from the "*" part of the SELECT.
# Everything but the "*" part is done inside the subquery sq.
# Then, once we know the ids
def get_best_streak_ironman(tour_id, to_max):
    sq = (VLife.objects
          .filter(tour_id=tour_id, sorties_total__gt=0, player__type='pilot',
                  # For some reason player__profile__id raises an error...
                  player__profile__nickname=OuterRef('player__profile__nickname'))
          .exclude(profile__is_hide=True)
          .order_by(to_max, '-score'))

    return VLife.objects.filter(pk=Subquery(sq.values('id')[:1]))


def pilot_vlife(request, vlife_id):
    try:
        vlife = (VLife.objects
                 .select_related('player', 'player__profile', 'player__tour')
                 .get(id=vlife_id, player__type='pilot'))
    except VLife.DoesNotExist:
        raise Http404
    return render(request, 'pilot_vlife.html', {
        'player': vlife.player,
        'vlife': vlife,
        'split_rankings': module_active(MODULE_SPLIT_RANKINGS),
        'ironman_stats:': module_active(MODULE_IRONMAN_STATS),
    })

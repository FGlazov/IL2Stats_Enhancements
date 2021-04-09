from datetime import timedelta

from django.conf import settings
from django.db.models import Q, Sum
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.urls import reverse

from mission_report.constants import Coalition

from stats.helpers import Paginator, get_sort_by, redirect_fix_url
from stats.models import (Player, Mission, PlayerMission, PlayerAircraft, Sortie, SortieStatus, KillboardPvP,
                          Tour, LogEntry, Profile, Squad, Reward, PlayerOnline, VLife)
from stats import sortie_log
from stats.views import *

from .variant_utils import has_juiced_variant, has_bomb_variant
from .aircraft_mod_models import AircraftBucket, AircraftKillboard, compute_float
from .bullets_types import render_ammo_breakdown

aircraft_sort_fields = ['total_sorties', 'total_flight_time', 'kd', 'khr', 'gkd', 'gkhr', 'accuracy',
                        'bomb_rocket_accuracy', 'plane_survivability', 'pilot_survivability', 'plane_lethality',
                        'pilot_lethality', 'elo', 'rating']
aircraft_killboard_sort_fields = ['kills', 'assists', 'deaths', 'kdr', 'plane_survivability', 'pilot_survivability',
                                  'plane_lethality', 'pilot_lethality']
ITEMS_PER_PAGE = 20


def all_aircraft(request, airfilter='NO_FILTER'):
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()
    sort_by = get_sort_by(request=request, sort_fields=aircraft_sort_fields, default='-rating')
    buckets = AircraftBucket.objects.filter(tour_id=request.tour.id, filter_type=airfilter,
                                            player=None).order_by(sort_by, 'id')
    if search:
        buckets = buckets.filter(aircraft__name__icontains=search)

    buckets = Paginator(buckets, ITEMS_PER_PAGE).page(page)

    return render(request, 'all_aircraft.html', {
        'all_aircraft': buckets,
        'filter_type': airfilter,
        'no_filter_url': all_aircraft_url(request.tour.id, 'NO_FILTER'),
        'no_mods_url': all_aircraft_url(request.tour.id, 'NO_BOMBS_JUICE'),
        'bombs_url': all_aircraft_url(request.tour.id, 'BOMBS'),
        'juiced_url': all_aircraft_url(request.tour.id, 'JUICE'),
        'all_mods_urls': all_aircraft_url(request.tour.id, 'ALL'),
    })


def all_aircraft_url(tour_id, filter_type):
    url = '{url}?tour={tour_id}'.format(url=reverse('stats:all_aircraft', args=[filter_type]),
                                        tour_id=tour_id)
    return url


def aircraft(request, aircraft_id, airfilter):
    bucket = find_aircraft_bucket(aircraft_id, request.GET.get('tour'), airfilter)
    if bucket is None:
        return render(request, 'aircraft_does_not_exist.html')

    ammo_breakdown = render_ammo_breakdown(bucket.ammo_breakdown)

    return render(request, 'aircraft.html', {
        'aircraft_bucket': bucket,
        'filter_option': airfilter,
        'ammo_breakdown': ammo_breakdown
    })


def aircraft_killboard(request, aircraft_id, airfilter):
    tour_id = request.GET.get('tour')
    enemy_filter = request.GET.get('enemy_filter', 'NO_FILTER')
    bucket = find_aircraft_bucket(aircraft_id, tour_id, airfilter)
    if bucket is None:
        return render(request, 'aircraft_does_not_exist.html')
    aircraft_id = int(aircraft_id)

    killboard = render_killboard(aircraft_id, airfilter, bucket, request, tour_id, enemy_filter, True)

    return render(request, 'aircraft_killboard.html', {
        'aircraft_bucket': bucket,
        'killboard': killboard,
        'enemy_filter': enemy_filter,
    })


def pilot_aircraft_overview(request, profile_id, airfilter, nickname=None):
    try:
        player = (Player.objects.select_related('profile', 'tour')
                  .get(profile_id=profile_id, type='pilot', tour_id=request.tour.id))
    except Player.DoesNotExist:
        raise Http404

    if player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=player.nickname)
    if player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'player': player})

    page = request.GET.get('page', 1)
    search = request.GET.get('search', '').strip()
    sort_by = get_sort_by(request=request, sort_fields=aircraft_sort_fields, default='-rating')
    buckets = (AircraftBucket.objects
               .filter(tour_id=request.tour.id, filter_type=airfilter, player=player)
               .order_by(sort_by, 'id'))
    if search:
        buckets = buckets.filter(aircraft__name__icontains=search)

    buckets = Paginator(buckets, ITEMS_PER_PAGE).page(page)

    return render(request, 'pilot_aircraft_overview.html', {
        'all_aircraft': buckets,
        'player': player,
        'filter_type': airfilter,
        'no_filter_url': pilot_aircraft_overview_url(profile_id, nickname, request.tour.id, 'NO_FILTER'),
        'no_mods_url': pilot_aircraft_overview_url(profile_id, nickname, request.tour.id, 'NO_BOMBS_JUICE'),
        'bombs_url': pilot_aircraft_overview_url(profile_id, nickname, request.tour.id, 'BOMBS'),
        'juiced_url': pilot_aircraft_overview_url(profile_id, nickname, request.tour.id, 'JUICE'),
        'all_mods_urls': pilot_aircraft_overview_url(profile_id, nickname, request.tour.id, 'ALL'),
    })


def pilot_aircraft_overview_url(profile_id, nickname, tour_id, filter_type):
    url = '{url}?tour={tour_id}'.format(
        url=reverse('stats:pilot_aircraft_overview', args=[profile_id, nickname, filter_type]),
        tour_id=tour_id)
    return url


def pilot_aircraft_killboard(request, profile_id, aircraft_id, airfilter, nickname=None):
    try:
        player = (Player.objects.select_related('profile', 'tour')
                  .get(profile_id=profile_id, type='pilot', tour_id=request.tour.id))
    except Player.DoesNotExist:
        raise Http404

    if player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=player.nickname)
    if player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'player': player})

    tour_id = request.GET.get('tour')
    enemy_filter = request.GET.get('enemy_filter', 'NO_FILTER')
    bucket = find_aircraft_bucket(aircraft_id, tour_id, airfilter, player)
    if bucket is None:
        return render(request, 'aircraft_does_not_exist.html')
    killboard = render_killboard(aircraft_id, airfilter, bucket, request, tour_id, enemy_filter, False)

    return render(request, 'pilot_aircraft_killboard.html', {
        'player': player,
        'aircraft_bucket': bucket,
        'killboard': killboard,
        'enemy_filter': enemy_filter,
    })


def render_killboard(aircraft_id, airfilter, bucket, request, tour_id, enemy_filter, no_players):
    aircraft_id = int(aircraft_id)
    unsorted_killboard = (AircraftKillboard.objects
                          .select_related('aircraft_1', 'aircraft_2')
                          .filter((Q(aircraft_1=bucket) & Q(aircraft_1__filter_type=airfilter)) |
                                  (Q(aircraft_2=bucket) & Q(aircraft_2__filter_type=airfilter)),
                                  (Q(aircraft_2=bucket) & Q(aircraft_1__filter_type=enemy_filter)) |
                                  (Q(aircraft_1=bucket) & Q(aircraft_2__filter_type=enemy_filter)),
                                  # Edge case: Killboards with only assists/distinct hits. Look strange.
                                  Q(aircraft_1_shotdown__gt=0) | Q(aircraft_2_shotdown__gt=0),
                                  tour__id=tour_id,
                                  ))
    if no_players:
        unsorted_killboard = unsorted_killboard.filter(aircraft_1__player=None, aircraft_2__player=None)

    killboard = []
    for k in unsorted_killboard:
        aircraft_1 = k.aircraft_1.aircraft
        if aircraft_1.id == aircraft_id:
            killboard.append(
                {'aircraft': k.aircraft_2.aircraft,
                 'kills': k.aircraft_1_shotdown,
                 'deaths': k.aircraft_2_shotdown,
                 'kdr': compute_float(k.aircraft_1_shotdown, k.aircraft_2_shotdown),
                 'plane_survivability': round(
                     100.0 - compute_float((k.aircraft_2_shotdown + k.aircraft_2_assists) * 100,
                                           k.aircraft_2_distinct_hits), 2),
                 'pilot_survivability': round(
                     100.0 - compute_float((k.aircraft_2_kills + k.aircraft_2_pk_assists) * 100,
                                           k.aircraft_2_distinct_hits), 2),
                 'plane_lethality': compute_float((k.aircraft_1_shotdown + k.aircraft_1_assists) * 100,
                                                  k.aircraft_1_distinct_hits),
                 'pilot_lethality': compute_float((k.aircraft_1_kills + k.aircraft_1_pk_assists) * 100,
                                                  k.aircraft_1_distinct_hits),
                 'url': k.get_aircraft_url(2),
                 }
            )
        else:
            killboard.append(
                {'aircraft': k.aircraft_1.aircraft,
                 'kills': k.aircraft_2_shotdown,
                 'deaths': k.aircraft_1_shotdown,
                 'kdr': compute_float(k.aircraft_2_shotdown, k.aircraft_1_shotdown),
                 'plane_survivability': round(
                     100.0 - compute_float((k.aircraft_1_shotdown + k.aircraft_1_assists) * 100,
                                           k.aircraft_1_distinct_hits), 2),
                 'pilot_survivability': round(
                     100.0 - compute_float((k.aircraft_1_kills + k.aircraft_1_pk_assists) * 100,
                                           k.aircraft_1_distinct_hits), 2),
                 'plane_lethality': compute_float((k.aircraft_2_shotdown + k.aircraft_2_assists) * 100,
                                                  k.aircraft_2_distinct_hits),
                 'pilot_lethality': compute_float((k.aircraft_2_kills + k.aircraft_2_pk_assists) * 100,
                                                  k.aircraft_2_distinct_hits),
                 'url': k.get_aircraft_url(1),
                 }
            )
    _sort_by = get_sort_by(request=request, sort_fields=aircraft_killboard_sort_fields, default='-kdr')
    sort_reverse = True if _sort_by.startswith('-') else False
    sort_by = _sort_by.replace('-', '')
    killboard = sorted(killboard, key=lambda x: x[sort_by], reverse=sort_reverse)
    return killboard


def pilot_aircraft(request, aircraft_id, airfilter, profile_id, nickname=None):
    try:
        player = (Player.objects.select_related('profile', 'tour')
                  .get(profile_id=profile_id, type='pilot', tour_id=request.tour.id))
    except Player.DoesNotExist:
        raise Http404

    if player.nickname != nickname:
        return redirect_fix_url(request=request, param='nickname', value=player.nickname)
    if player.profile.is_hide:
        return render(request, 'pilot_hide.html', {'player': player})

    bucket = find_aircraft_bucket(aircraft_id, request.GET.get('tour'), airfilter, player)
    if bucket is None:
        return render(request, 'aircraft_does_not_exist.html')

    ammo_breakdown = render_ammo_breakdown(bucket.ammo_breakdown, filter_out_flukes=False)

    return render(request, 'pilot_aircraft.html', {
        'player': player,
        'aircraft_bucket': bucket,
        'filter_option': airfilter,
        'ammo_breakdown': ammo_breakdown
    })


def find_aircraft_bucket(aircraft_id, tour_id, bucket_filter, player=None):
    if tour_id:
        try:
            bucket = (AircraftBucket.objects.select_related('aircraft', 'tour')
                      .get(aircraft=aircraft_id, tour_id=tour_id, filter_type=bucket_filter, player=player))
        except AircraftBucket.DoesNotExist:
            bucket = None
    else:
        try:
            bucket = (AircraftBucket.objects.select_related('aircraft', 'tour')
                      .filter(aircraft=aircraft_id, filter_type=bucket_filter, player=player)
                      .order_by('-id'))[0]
        except IndexError:
            raise Http404
    return bucket

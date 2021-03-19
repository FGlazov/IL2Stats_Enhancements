from datetime import timedelta

from django.conf import settings
from django.db.models import Q, Sum
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.urls import reverse

from mission_report.constants import Coalition

from stats.helpers import Paginator, get_sort_by, redirect_fix_url
from stats.models import (Player, Mission, PlayerMission, PlayerAircraft, Sortie, KillboardPvP,
                          Tour, LogEntry, Profile, Squad, Reward, PlayerOnline, VLife)
from stats import sortie_log
from stats.views import *
from .aircraft_mod_models import AircraftBucket, AircraftKillboard, compute_float

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
    buckets = AircraftBucket.objects.filter(tour_id=request.tour.id, filter_type=airfilter).order_by(sort_by, 'id')
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

    return render(request, 'aircraft.html', {
        'aircraft_bucket': bucket,
        'filter_option': airfilter,
    })


def aircraft_killboard(request, aircraft_id, airfilter):
    tour_id = request.GET.get('tour')
    bucket = find_aircraft_bucket(aircraft_id, tour_id, airfilter)
    if bucket is None:
        return render(request, 'aircraft_does_not_exist.html')
    aircraft_id = int(aircraft_id)

    unsorted_killboard = (AircraftKillboard.objects
                          .select_related('aircraft_1', 'aircraft_2')
                          .filter((Q(aircraft_1=bucket) & Q(aircraft_1__filter_type=airfilter)) |
                                  (Q(aircraft_2=bucket) & Q(aircraft_2__filter_type=airfilter)),
                                  # Edge case: Killboards with only assists/distinct hits. Look strange.
                                  Q(aircraft_1_shotdown__gt=0) | Q(aircraft_2_shotdown__gt=0),
                                  tour__id=tour_id,
                                  ))

    killboard = []
    for k in unsorted_killboard:
        aircraft_1 = k.aircraft_1.aircraft
        if aircraft_1.id == aircraft_id:
            if not allow_killboard_line(k.aircraft_1, k.aircraft_2):
                continue

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
            if not allow_killboard_line(k.aircraft_2, k.aircraft_1):
                continue

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

    return render(request, 'aircraft_killboard.html', {
        'aircraft_bucket': bucket,
        'killboard': killboard,
    })


def allow_killboard_line(our_aircraft, enemy_aircraft):
    b = our_aircraft
    # Technically speaking this function could be folded into the query and it would likely be quicker.
    # The logic here is so complicated, that it is IMO more readable as a separate python function.
    # Not much performance lost anyways - it's at most 50 objects which are iterated over in (slow) python.

    if enemy_aircraft.has_juiced_variant and enemy_aircraft.has_bomb_variant:
        return our_aircraft.filter_type == enemy_aircraft.filter_type
    elif enemy_aircraft.has_juiced_variant:
        if our_aircraft.filter_type == b.BOMBS:
            return enemy_aircraft.filter_type == b.NO_FILTER
        elif our_aircraft.filter_type == b.ALL:
            return enemy_aircraft.filter_type == b.JUICED
        else:
            return our_aircraft.filter_type == enemy_aircraft.filter_type
    elif enemy_aircraft.has_bomb_variant:
        if our_aircraft.filter_type == b.JUICED:
            return enemy_aircraft.filter_type == b.NO_FILTER
        elif our_aircraft.filter_type == b.ALL:
            return enemy_aircraft.filter_type == b.BOMBS
        else:
            return our_aircraft.filter_type == enemy_aircraft.filter_type
    else:
        return True  # Enemy aircraft type is always NO_FILTER, so there are no duplicates here anyways.


def find_aircraft_bucket(aircraft_id, tour_id, bucket_filter):
    if tour_id:
        try:
            bucket = (AircraftBucket.objects.select_related('aircraft', 'tour')
                      .get(aircraft=aircraft_id, tour_id=tour_id, filter_type=bucket_filter))
        except AircraftBucket.DoesNotExist:
            bucket = None
    else:
        try:
            bucket = (AircraftBucket.objects.select_related('aircraft', 'tour')
                      .filter(aircraft=aircraft_id, filter_type=bucket_filter)
                      .order_by('-id'))[0]
        except IndexError:
            raise Http404
    return bucket

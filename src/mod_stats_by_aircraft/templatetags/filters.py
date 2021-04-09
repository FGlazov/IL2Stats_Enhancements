from django import template
from django.urls import reverse
from ..aircraft_mod_models import get_killboard_url

register = template.Library()


@register.filter()
def seconds_to_long_time(value):
    total_minutes, seconds = divmod(value, 60)
    total_hours, minutes = divmod(total_minutes, 60)
    total_days, hours = divmod(total_hours, 24)
    if total_days:
        return '%d:%02d:%02d' % (total_days, hours, minutes)
    else:
        return '%d:%02d' % (total_hours, minutes)


@register.filter()
def get_killboard_url_no_filter(value, arg='NO_FILTER'):
    bucket = value
    enemy_filter = arg

    return get_killboard_url(bucket.aircraft.id, bucket.tour.id, bucket.player, bucket.NO_FILTER, enemy_filter)


@register.filter()
def get_killboard_bombs(value, arg='NO_FILTER'):
    bucket = value
    enemy_filter = arg

    return get_killboard_url(bucket.aircraft.id, bucket.tour.id, bucket.player, bucket.BOMBS, enemy_filter)


@register.filter()
def get_killboard_no_mods(value, arg='NO_FILTER'):
    bucket = value
    enemy_filter = arg

    return get_killboard_url(bucket.aircraft.id, bucket.tour.id, bucket.player, bucket.NO_BOMBS_NO_JUICE, enemy_filter)


@register.filter()
def get_killboard_juiced(value, arg='NO_FILTER'):
    bucket = value
    enemy_filter = arg

    return get_killboard_url(bucket.aircraft.id, bucket.tour.id, bucket.player, bucket.JUICED, enemy_filter)


@register.filter()
def get_killboard_all_mods(value, arg='NO_FILTER'):
    bucket = value
    enemy_filter = arg

    return get_killboard_url(bucket.aircraft.id, bucket.tour.id, bucket.player, bucket.ALL, enemy_filter)
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from stats.logger import logger
import os
import codecs
import errno

from .aircraft_mod_models import multi_key_to_string

OFFENSIVE_BREAKDOWN = 'OFFENSIVE_BREAKDOWN'
DEFENSIVE_BREAKDOWN = 'DEFENSIVE_BREAKDOWN'
BREAKDOWN_TYPES = {OFFENSIVE_BREAKDOWN, DEFENSIVE_BREAKDOWN}


def write_breakdown_line(aircraft_bucket, damage_report, breakdown_type, other_aircraft, pilot_snipe):
    """
    Format of csv is AMMO_TYPE_1, AMMO_TYPE_2, ..., AMMO_TYPE_X, attacker, target, pilot_snipe

    The AMMO_TYPE_* are sorted alphabetically. Each line represents a single aircraft death. This function is
    responsible for appending one line to the .csv. This .csv is later served on the website, so that users can
    analyze the date in more depth.

    @param aircraft_bucket The aircraft bucket which is to be incremented.
    @param damage_report How many hits were required for the downing. Dict - keys are projectile types, values are
    how many hits from that projectile type were done.
    @param breakdown_type The breakdown type - a bucket may have multiple breakdowns of the same ammo.
    @param other_aircraft The other object (usually an aircraft) participating in this aircraft death. Either the target
    or attacker, depending on on breakdown_type.
    @param pilot_snipe Whether the aircraft got shotdown by pilot snipe.
    """
    if breakdown_type not in BREAKDOWN_TYPES:
        logger.warning('[mod_stats_by_aircraft] Unknown breakdown type:' + str(breakdown_type))
        return

    line = ''
    for ammo_key in sorted(list(damage_report.keys())):
        line += str(damage_report[ammo_key]) + ','

    if breakdown_type == OFFENSIVE_BREAKDOWN:
        # Attacker first: That's our aircraft
        # Target second: That's the other aircraft.
        line += aircraft_bucket.aircraft.name_en + ',' + other_aircraft.name_en + ','
    else:  # breakdown_type == DEFENSIVE_BREAKDOWN
        # Attacker first: That's the other aircraft
        # Target second: That's our aircraft.
        line += other_aircraft.name_en + ',' + aircraft_bucket.aircraft.name_en + ','

    line += str(pilot_snipe) + '\n'

    path = get_breakdown_path(aircraft_bucket.tour.id, aircraft_bucket,
                              multi_key_to_string(list(damage_report.keys()), separator='__'), breakdown_type)
    if not os.path.isfile(path):
        initialize_csv(path, list(damage_report.keys()))
    with codecs.open(path, 'a', 'utf-8') as f:
        f.write(line)


def download_breakdown_csv(bucket, ammo_key, breakdown_type):
    ammo_key = ammo_key.replace('|', '__')
    path = get_breakdown_path(bucket.tour.id, bucket, ammo_key, breakdown_type)
    if breakdown_type not in BREAKDOWN_TYPES:
        raise Http404
    if not path.startswith(os.path.abspath(settings.MEDIA_ROOT) + os.sep):
        raise PermissionDenied

    if os.path.exists(path):
        with open(path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(path)
            return response
    else:
        raise Http404


def initialize_csv(path, ammo_keys):
    line = ''
    for ammo_key in sorted(ammo_keys):
        line += ammo_key + ','
    line += 'attacker, target, pilot_snipe\n'

    try:
        os.makedirs(os.path.dirname(path))
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise

    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(line)


def get_breakdown_path(tour_id, bucket, ammo_key, breakdown_type):
    return os.path.join(settings.MEDIA_ROOT, 'ammo_breakdowns', str(tour_id), str(bucket.id), ammo_key,
                        bucket.aircraft.name_en + '_Tour_' + str(tour_id) + '_' + breakdown_type + '.csv')

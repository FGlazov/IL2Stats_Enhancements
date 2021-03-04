from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Q
from django.utils import timezone
import time
import datetime
from django.utils.timezone import make_aware

from stats.models import (Object, Mission, Sortie, Profile, Player, PlayerAircraft, VLife,
                          PlayerMission, KillboardPvP, Tour, LogEntry, Score, Squad)


class Command(BaseCommand):
    help = 'Retroactively calculate split rankings. All sorties before the time cut off (by default when the program is ' \
           'started) are used to add to the split rankings. '

    def add_arguments(self, parser):
        parser.add_argument('-t', '--time', type=int, help='Number in unix time in seconds which determines the cutoff'
                                                           ' for which sorties are considered. Should be the time just'
                                                           ' as this mod was installed.')

    def handle(self, *args, **options):
        # TODO: Input time as a parameter.
        if options['time'] is not None:
            cutoff_time = datetime.datetime.fromtimestamp(options['time'])
            cutoff_time = make_aware(cutoff_time)
        else:
            cutoff_time = timezone.now()

        print("Cut off time is " + str(cutoff_time) + " -- It should correspond to the time you have first installed "
                                                      "this mod.")
        input("Press Enter to continue.")

        sorties = Sortie.objects.filter(date_start__lt=cutoff_time)
        sorties_count = sorties.count()
        print("Retroactively computing split rankings for {} sorties".format(sorties_count))

        # Use a paginator-like pattern. Prevents too much memory usage.
        pointer = 0
        batch_size = 250
        while pointer < sorties_count:
            print("Progress: {0:.2%}".format(pointer / sorties_count))
            for sortie in sorties[pointer:pointer + batch_size]:
                add_split_rankings(sortie)
            pointer += batch_size

        print("Done retroactively computing split rankings!")


def add_split_rankings(sortie):
    player = sortie.player
    vlife = sortie.vlife
    player_mission = PlayerMission.objects.get(profile_id=sortie.profile.id, player_id=player.id,
                                               mission_id=sortie.mission.id)
    update_general(player, sortie)
    update_general(vlife, sortie)
    update_general(player_mission, sortie)
    if player.squad:
        update_general(player.squad, sortie)

    player.score_streak_current_heavy = vlife.score_heavy
    player.score_streak_current_medium = vlife.score_medium
    player.score_streak_current_light = vlife.score_light
    player.score_streak_max_heavy = max(player.score_streak_max_heavy, player.score_streak_current_heavy)
    player.score_streak_max_medium = max(player.score_streak_max_medium, player.score_streak_current_medium)
    player.score_streak_max_light = max(player.score_streak_max_light, player.score_streak_current_light)

    vlife.save()
    player_mission.save()
    player.save()

def update_general(player, sortie):
    relive_add = 1 if sortie.is_relive else 0
    try:
        if not sortie.is_not_takeoff:
            if sortie.aircraft.cls == "aircraft_light":
                player.score_light += sortie.score
                player.flight_time_light += sortie.flight_time
                player.relive_light += relive_add
            elif sortie.aircraft.cls == "aircraft_medium":
                player.score_medium += sortie.score
                player.flight_time_medium += sortie.flight_time
                player.relive_medium += relive_add
            elif sortie.aircraft.cls == "aircraft_heavy":
                player.score_heavy += sortie.score
                player.flight_time_heavy += sortie.flight_time
                player.relive_heavy += relive_add
    except AttributeError:
        pass # Vlife doesn't have flight_time/relive.
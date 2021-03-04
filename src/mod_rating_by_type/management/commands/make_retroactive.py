from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime
import time
from django.utils.timezone import make_aware
from django.db import transaction

from stats.models import (Object, Mission, Sortie, Profile, Player, PlayerAircraft, VLife,
                          PlayerMission, KillboardPvP, Tour, LogEntry, Score, Squad)


class Command(BaseCommand):
    help = 'Retroactively calculate split rankings. All sorties before the time cut off (by default when the program is ' \
           'started) are used to add to the split rankings. '

    def add_arguments(self, parser):
        parser.add_argument('-t', '--time', type=int, help='Number in unix time in seconds which determines the cutoff'
                                                           ' for which sorties are considered. Should be the time just'
                                                           ' as version >=1.2.48 of IL-2 stats was installed.')

    def handle(self, *args, **options):
        if options['time'] is not None:
            cutoff_time = datetime.datetime.fromtimestamp(options['time'])
            cutoff_time = make_aware(cutoff_time)
        else:
            cutoff_time = timezone.now()
        print("\n=====================================================================================================")
        print("Cutoff time is " + str(cutoff_time))
        print("Cutoff time as unix time (to pass as a -t param): " + str(int(time.mktime(cutoff_time.timetuple()))))

        print("\nNo sorties after version >=1.2.48 of IL-2 stats have been installed should be present after the cutoff")
        print("time. If there any sorties after the cut off time, then you may specify the cutoff time via a -t")
        print("parameter (as unix time in seconds). Any sorties after the cutoff time will count twice towards")
        print("split rankings.")
        print("\n")
        print("IMPORTANT: Make sure that stats.cmd is NOT running. Waitress.cmd is not affected.")
        print("Otherwise you'll likely cause stats.cmd or this process to crash.")
        print("You may quit this script at any time if you wish to run stats.cmd!")
        print("This script will pick up where you left off if you quit it.")
        print("Just make sure to save your cutoff time and pass it into the script later!")
        print("\n")
        input("Press Enter to continue.")

        sorties = Sortie.objects.filter(date_start__lt=cutoff_time, debug__retrosplitmod__isnull=True)
        sorties_count = sorties.count()
        print("Retroactively computing split rankings for {} sorties".format(sorties_count))

        # Only get 500 sorties at a time. Prevents too much memory usage.
        batch_size = 500
        county = 0
        done_pages = 0

        while done_pages < sorties_count:
            with transaction.atomic():
                print("Progress: {0:.4%} | {1} sorties processed".format(done_pages / sorties_count, done_pages))
                # One does not need to iterate the slice by page.
                # We're marking the sorties in one such batch as "done", and the query does not find them later.
                for sortie in sorties[0:batch_size]:
                    add_split_rankings(sortie)
                done_pages += batch_size
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

    # Hacky solution to makesure that a sortie is not retroactively added twice.
    sortie.debug['retrosplitmod'] = 1

    vlife.save()
    player_mission.save()
    player.save()
    sortie.save()


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
        pass  # Vlife doesn't have flight_time/relive.

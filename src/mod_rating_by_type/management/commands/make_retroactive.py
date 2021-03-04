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
        parser.add_argument('-t' ,'--time', type=int, help='Number in unix time in seconds which determines the cutoff'
                                                          ' for which sorties are considered. Should be the time just'
                                                          ' as this mod was installed.')

    def handle(self, *args, **options):
        # TODO: Input time as a parameter.
        if options['time'] is not None:
            cutoff_time = datetime.datetime.fromtimestamp(options['time'])
            cutoff_time = make_aware(cutoff_time)
        else:
            cutoff_time = timezone.now()

        print("Cut off time is " + str(cutoff_time))
        input("Press Enter to continue.")


        sorties_count = Sortie.objects.filter(date_start__lt=cutoff_time).count()

        print("Retroactively computing split rankings for {} sorties".format(sorties_count))

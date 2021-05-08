from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from stats.models import Sortie, Player


class SortieAugmentation(models.Model):
    """
    Additional fields to Sortie objects used by this mod.
    """
    sortie = models.OneToOneField(Sortie, on_delete=models.PROTECT, primary_key=True,
                                  related_name='SortieAugmentation_MOD_SPLIT_RANKINGS')

    CLASSES = (
        ('heavy', 'heavy'),
        ('medium', 'medium'),
        ('light', 'light'),
        ('placeholder', 'placeholder')
    )

    # This class differs from the cls found in a Sortie object.
    # Namely: Jabo flights are considred "medium", and P-38/Me-262 without bombs are considered "light"
    # In all other cases, it should be equal to the one found in
    cls = models.CharField(choices=CLASSES, max_length=16, blank=True)

    class Meta:
        # The long table name is to avoid any conflicts with new tables defined in the main branch of IL2 Stats.
        db_table = "Sortie_MOD_SPLIT_RANKINGS"


class PlayerAugmentation(models.Model):
    """
    Additional fields to Player objects used by this mod.
    """

    player = models.OneToOneField(Player, on_delete=models.PROTECT, primary_key=True,
                                  related_name='PlayerAugmentation_MOD_SPLIT_RANKINGS')

    # Between -3 and +3. +3 means last 3 jabo/attacker sorties were judged as fighters, -3 means judged as attackers.
    fighter_attacker_counter = models.IntegerField(default=0, validators=[MinValueValidator(-3), MaxValueValidator(3)])

    class Meta:
        # The long table name is to avoid any conflicts with new tables defined in the main branch of IL2 Stats.
        db_table = "Player_MOD_SPLIT_RANKINGS"

    def increment_attacker_plane_as_fighter(self):
        self.fighter_attacker_counter = min(self.fighter_attacker_counter + 1, 3)

    def increment_attacker_plane_as_attacker(self):
        self.fighter_attacker_counter = max(self.fighter_attacker_counter - 1, -3)

    def decide_ambiguous_fighter_attacker_sortie(self):
        if self.fighter_attacker_counter > 0:
            return 'light'
        elif self.fighter_attacker_counter < 0:
            return 'medium'
        else:
            return None

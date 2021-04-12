from django.db import models
from stats.models import Sortie


# Additional fields to Sortie objects used by this mod.
class SortieAugmentation(models.Model):
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

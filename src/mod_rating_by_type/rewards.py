from functools import lru_cache

from custom import rewards
from stats.models import Award, VLife
from .models import FilteredReward, VLifeAugmentation

_awards_tour = Award.objects.filter(type='tour')
_awards_mission = Award.objects.filter(type='mission')
_awards_sortie = Award.objects.filter(type='sortie')
_awards_vlife = Award.objects.filter(type='vlife')


@lru_cache(maxsize=32)
def get_reward_func(func_name):
    return getattr(rewards, func_name)


@lru_cache(maxsize=512)
def rewarding(award_id, player_id):
    return FilteredReward.objects.get_or_create(award_id=award_id, player_id=player_id)


def reward_tour(player):
    for award in _awards_tour:
        if get_reward_func(award.func)(player=player):
            rewarding(award_id=award.id, player_id=player.id)


def reward_mission(player_mission, player):
    for award in _awards_mission:
        if get_reward_func(award.func)(player_mission=player_mission):
            rewarding(award_id=award.id, player_id=player.id)


def reward_sortie(sortie, player):
    for award in _awards_sortie:
        if get_reward_func(award.func)(sortie=sortie):
            rewarding(award_id=award.id, player_id=player.id)


def reward_vlife(vlife, player):
    for award in _awards_vlife:
        if get_reward_func(award.func)(vlife=vlife):
            rewarding(award_id=award.id, player_id=player.id)


def reward_vlife_patch(vlife):
    player = vlife.player
    for award in _awards_vlife:
        if get_reward_func(award.func)(vlife=vlife):
            rewarding(award_id=award.id, player_id=player.id)

    if vlife.id is None:
        return

    ak_no_ai = vlife.ak_total
    killboard = vlife.killboard_pve
    aircraft_types = ['aircraft_light', 'aircraft_medium', 'aircraft_heavy', 'aircraft_transport']
    for aircraft_type in aircraft_types:
        ak_no_ai -= killboard[aircraft_type] if aircraft_type in killboard else 0

    augmentation = VLifeAugmentation.objects.get_or_create(vlife=vlife)[0]
    augmentation.ak_no_ai = ak_no_ai
    augmentation.save()

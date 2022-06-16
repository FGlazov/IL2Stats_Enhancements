from django.db.models import Q, F

from .aircraft_mod_models import AircraftBucket, SortieAugmentation, AircraftKillboard
from .variant_utils import has_juiced_variant, has_bomb_variant, get_sortie_type
from .ammo_file_manager import write_breakdown_line, OFFENSIVE_BREAKDOWN, DEFENSIVE_BREAKDOWN
from .apps import IGNORE_AI_KILLS_STREAKS

from stats.models import Sortie, LogEntry, Player, Object
from stats.logger import logger


def process_aircraft_stats(sortie, player=None, is_retro_compute=False):
    """
    Takes a Sortie, and increments the corresponding data in AircraftBucket.

    Note that there might be several aircraft buckets.

    Passing sortie.player into player will update the AircraftBuckets with player.
    """
    if not sortie.aircraft.cls_base == "aircraft":
        return

    bucket = (AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                   filter_type='NO_FILTER', player=player))[0]

    has_subtype = has_juiced_variant(bucket.aircraft) or has_bomb_variant(bucket.aircraft)

    process_bucket(bucket, sortie, has_subtype, False, is_retro_compute)

    if has_subtype:
        filtered_bucket = (AircraftBucket.objects.get_or_create(tour=sortie.tour, aircraft=sortie.aircraft,
                                                                filter_type=get_sortie_type(sortie), player=player))[0]
        process_bucket(filtered_bucket, sortie, True, True, is_retro_compute)


def process_bucket(bucket, sortie, has_subtype, is_subtype, is_retro_compute):
    if not sortie.is_not_takeoff:
        bucket.total_sorties += 1
        bucket.total_flight_time += sortie.flight_time
    bucket.kills += sortie.ak_total
    bucket.ground_kills += sortie.gk_total
    bucket.assists += sortie.ak_assist
    bucket.aircraft_lost += 1 if sortie.is_lost_aircraft else 0
    bucket.score += sortie.score
    bucket.deaths += 1 if sortie.is_dead else 0
    bucket.captures += 1 if sortie.is_captured and not sortie.is_dead else 0
    bucket.bailouts += 1 if sortie.is_bailout else 0
    bucket.ditches += 1 if sortie.is_ditched else 0
    bucket.landings += 1 if sortie.is_landed else 0
    bucket.in_flight += 1 if sortie.is_in_flight else 0
    bucket.crashes += 1 if sortie.is_crashed else 0
    bucket.shotdown += 1 if sortie.is_shotdown else 0
    bucket.coalition = sortie.coalition
    increment_ammo(bucket, sortie)
    if sortie.damage:
        bucket.sorties_plane_was_hit += 1
        bucket.plane_survivability_counter += 1 if not sortie.is_lost_aircraft else 0
        bucket.pilot_survivability_counter += 1 if not sortie.is_relive else 0
    for key in sortie.killboard_pvp:
        value = sortie.killboard_pvp[key]
        if key in bucket.killboard_planes:
            bucket.killboard_planes[key] += value
        else:
            bucket.killboard_planes[key] = value
    for key in sortie.killboard_pve:
        value = sortie.killboard_pve[key]
        if key in bucket.killboard_ground:
            bucket.killboard_ground[key] += value
        else:
            bucket.killboard_ground[key] = value

    from .background_jobs.run_background_jobs import retro_streak_compute_running
    if bucket.player is not None and ((not retro_streak_compute_running()) or is_retro_compute):
        process_streaks_and_best_sorties(bucket, sortie)

    process_log_entries(bucket, sortie, has_subtype, is_subtype)

    sortie_augmentation = (SortieAugmentation.objects.get_or_create(sortie=sortie))[0]
    if not bucket.player:
        sortie_augmentation.sortie_stats_processed = True
    else:
        sortie_augmentation.player_stats_processed = True
    sortie_augmentation.fixed_aa_accident_stats = True
    sortie_augmentation.fixed_doubled_turret_killboards = True
    sortie_augmentation.added_player_kb_losses = True
    sortie_augmentation.fixed_accuracy = True
    sortie_augmentation.recomputed_ammo_breakdown = True
    sortie_augmentation.recomputed_ammo_breakdown_2 = True
    sortie_augmentation.fixed_captures = True

    sortie_augmentation.save()


def increment_ammo(bucket, sortie):
    if sortie.is_bailout:
        return  # Bug work around. Bailout results in all ammo being used according to logs.

    takeoff_count = LogEntry.objects.filter(
        act_sortie_id=sortie.id,
        type='takeoff'
    ).count()
    if takeoff_count > 1:
        return  # Bug work around. Rearming (and as such taking off twice) resets ammo used according to logs.

    if sortie.ammo['used_cartridges']:
        bucket.ammo_shot += sortie.ammo['used_cartridges']
    if sortie.ammo['hit_bullets']:
        bucket.ammo_hit += sortie.ammo['hit_bullets']
    if sortie.ammo['used_bombs']:
        bucket.bomb_rocket_shot += sortie.ammo['used_bombs']
    if sortie.ammo['hit_bombs']:
        bucket.bomb_rocket_hit += sortie.ammo['hit_bombs']
    if sortie.ammo['used_rockets']:
        bucket.bomb_rocket_shot += sortie.ammo['used_rockets']
    if sortie.ammo['hit_rockets']:
        bucket.bomb_rocket_hit += sortie.ammo['hit_rockets']


def decrement_ammo_bugged(bucket, sortie):
    """
    For retroactive fixing, this reverses increment_ammo on a given sortie.
    """
    takeoff_count = LogEntry.objects.filter(
        act_sortie_id=sortie.id,
        type='takeoff'
    ).count()

    if takeoff_count <= 1 and not sortie.is_bailout:
        return

    if sortie.ammo['used_cartridges']:
        bucket.ammo_shot -= sortie.ammo['used_cartridges']
    if sortie.ammo['hit_bullets']:
        bucket.ammo_hit -= sortie.ammo['hit_bullets']
    if sortie.ammo['used_bombs']:
        bucket.bomb_rocket_shot -= sortie.ammo['used_bombs']
    if sortie.ammo['hit_bombs']:
        bucket.bomb_rocket_hit -= sortie.ammo['hit_bombs']
    if sortie.ammo['used_rockets']:
        bucket.bomb_rocket_shot -= sortie.ammo['used_rockets']
    if sortie.ammo['hit_rockets']:
        bucket.bomb_rocket_hit -= sortie.ammo['hit_rockets']


def process_log_entries(bucket, sortie, has_subtype, is_subtype, stop_update_primary_bucket=False,
                        compute_only_pure_killboard_stats=False, do_not_use_pilot_kbs=False):
    events = (LogEntry.objects
              .select_related('act_object', 'act_sortie', 'cact_object', 'cact_sortie')
              .filter(Q(act_sortie_id=sortie.id),
                      Q(type='shotdown') | Q(type='killed') | Q(type='damaged'),
                      act_object__cls_base='aircraft', cact_object__cls_base='aircraft',
                      # Disregard AI sorties
                      act_sortie_id__isnull=False, cact_sortie_id__isnull=False, )
              # Disregard friendly fire incidents.
              .exclude(act_sortie__coalition=F('cact_sortie__coalition')))

    enemies_damaged = set()
    enemies_shotdown = set()
    enemies_killed = set()

    for event in events:
        enemy_sortie = Sortie.objects.filter(id=event.cact_sortie_id).get()

        enemy_plane_sortie_pair = (event.cact_object, enemy_sortie)
        if event.type == 'damaged':
            enemies_damaged.add(enemy_plane_sortie_pair)
        elif event.type == 'shotdown':
            enemies_shotdown.add(enemy_plane_sortie_pair)
        elif event.type == 'killed':
            enemies_killed.add(enemy_plane_sortie_pair)

    use_pilot_kbs = bucket.player is None
    if do_not_use_pilot_kbs:
        use_pilot_kbs = False
    enemy_buckets, kbs = update_from_entries(bucket, enemies_damaged, enemies_killed, enemies_shotdown,
                                             has_subtype, is_subtype, use_pilot_kbs,
                                             update_primary_bucket=not stop_update_primary_bucket)

    for killboard in kbs.values():
        killboard.reset_kills_turret_bug = True
        killboard.reset_player_loses = True
        killboard.save()
    for enemy_bucket in enemy_buckets.values():
        enemy_bucket.update_derived_fields()
        enemy_bucket.save()

    # LogEntry does not store what your turrets did. Only what turrets hit you.
    # So we parse all turret encounters from the perspective of the turret's plane.
    turret_events = (LogEntry.objects
                     .select_related('act_object', 'act_sortie', 'cact_object', 'cact_sortie')
                     .filter(Q(cact_sortie_id=sortie.id),
                             Q(type='shotdown') | Q(type='killed') | Q(type='damaged'),
                             act_object__cls='aircraft_turret', cact_object__cls_base='aircraft',
                             # Filter out AI kills from turret.
                             cact_sortie_id__isnull=False)

                     # Disregard friendly fire incidents.
                     .exclude(extra_data__is_friendly_fire=True))

    enemies_damaged = set()
    enemies_shotdown = set()
    enemies_killed = set()

    if not compute_only_pure_killboard_stats:
        process_aa_accident_death(bucket, sortie)
        if 'ammo_breakdown' in sortie.ammo:
            process_ammo_breakdown(bucket, sortie, is_subtype)

    if not stop_update_primary_bucket:
        bucket.update_derived_fields()
        bucket.save()

    if len(turret_events) > 0 and not is_subtype:
        cache_turret_buckets = dict()

        for event in turret_events:
            turret_name = event.act_object.name
            if turret_name not in cache_turret_buckets:
                log_name = event.act_object.log_name
                turret_bucket = turret_to_aircraft_bucket(turret_name, log_name, bucket.tour)
                if turret_bucket is None:
                    continue
                cache_turret_buckets[turret_name] = turret_bucket
            if event.type == 'damaged':
                enemies_damaged.add(turret_name)
            elif event.type == 'shotdown':
                enemies_shotdown.add(turret_name)
            elif event.type == 'killed':
                enemies_killed.add(turret_name)

        for turret_name in cache_turret_buckets:
            turret_bucket = cache_turret_buckets[turret_name]
            enemy_damaged = set()
            if turret_name in enemies_damaged:
                enemy_damaged.add((bucket.aircraft, sortie))
            enemy_shotdown = set()
            if turret_name in enemies_shotdown:
                enemy_shotdown.add((bucket.aircraft, sortie))
            enemy_killed = set()
            if turret_name in enemies_killed:
                enemy_killed.add((bucket.aircraft, sortie))

            update_primary_bucket = bucket.player is None
            if stop_update_primary_bucket:
                update_primary_bucket = False
            use_pilot_kbs = bucket.player is not None
            if do_not_use_pilot_kbs:
                use_pilot_kbs = False

            buckets, kbs = update_from_entries(turret_bucket, enemy_damaged, enemy_killed, enemy_shotdown,
                                               # We can't determine the subtype of the bomber
                                               # Edge case: Halberstadt. It is turreted and has a jabo variant.
                                               # This should be fixed somehow in the long run.
                                               False, False, use_pilot_kbs, update_primary_bucket)
            if not stop_update_primary_bucket:
                turret_bucket.update_derived_fields()
                turret_bucket.save()
            for bucket in buckets.values():
                bucket.update_derived_fields()
                bucket.save()

            for kb in kbs.values():
                kb.reset_kills_turret_bug = True
                kb.reset_player_loses = True
                kb.save()


def update_from_entries(bucket, enemies_damaged, enemies_killed, enemies_shotdown, has_subtype, is_subtype,
                        use_pilot_kbs, update_primary_bucket):
    cache_kb = dict()
    cache_enemy_buckets_kb = dict()  # Helper cache needed in order to find buckets (quickly) inside get_killboard.
    for damaged_enemy in enemies_damaged:
        enemy_sortie = damaged_enemy[1]
        kbs = get_killboards(damaged_enemy, bucket, cache_kb, cache_enemy_buckets_kb, use_pilot_kbs,
                             update_primary_bucket)
        for kb in kbs:
            update_damaged_enemy(bucket, damaged_enemy, enemies_killed, enemies_shotdown, enemy_sortie, kb,
                                 update_primary_bucket)

    cache_enemy_buckets = dict()
    for shotdown_enemy in enemies_shotdown:
        enemy_sortie = shotdown_enemy[1]
        enemy_sortie_type = get_sortie_type(enemy_sortie)

        subtype_enemy_bucket_key = (bucket.tour, shotdown_enemy[0], enemy_sortie_type)
        subtype_enemy_bucket = ensure_bucket_in_cache(cache_enemy_buckets, subtype_enemy_bucket_key, None)
        if bucket.player is None and update_primary_bucket:
            update_elo(bucket, cache_enemy_buckets, enemy_sortie_type, has_subtype, is_subtype, shotdown_enemy,
                       subtype_enemy_bucket)

        kbs = get_killboards(shotdown_enemy, bucket, cache_kb, cache_enemy_buckets_kb, use_pilot_kbs,
                             update_primary_bucket)
        for kb in kbs:
            if kb.aircraft_1.aircraft == bucket.aircraft:
                kb.aircraft_1_shotdown += 1
            else:
                kb.aircraft_2_shotdown += 1
    for killed_enemy in enemies_killed:
        if update_primary_bucket:
            bucket.pilot_kills += 1
        kbs = get_killboards(killed_enemy, bucket, cache_kb, cache_enemy_buckets_kb, use_pilot_kbs,
                             update_primary_bucket)
        for kb in kbs:
            if kb.aircraft_1.aircraft == bucket.aircraft:
                kb.aircraft_1_kills += 1
            else:
                kb.aircraft_2_kills += 1
    return cache_enemy_buckets, cache_kb


def update_elo(bucket, cache_enemy_buckets, enemy_sortie_type, has_subtype, is_subtype, shotdown_enemy,
               subtype_enemy_bucket):
    """
    # TODO: Refactor elo functions into new file.

    Computes changes to AircraftBucket.elo field. Note that Elo is zero-sum, thus two buckets must always be updated.

    There are in essence three cases for the Elo Update:

    Aircraft 1 and Aircraft 2 have no subtypes -> Just update elo directly.
    Aircraft 1 and 2 have subtypes: Main types update each other. Subtypes update each other.
    Aircraft 1 has subtypes, Aircraft 2 does not:
    Aircraft 1 main type and subtype updates directly from Aircraft 2 only type
    Aircraft 2 has "half an encounter" with aircraft 1 main type, and "half an encounter" with aircraft 1 subtype.
    """
    if enemy_sortie_type == bucket.NO_FILTER:  # No subtypes for enemy
        if not has_subtype:
            bucket.elo, subtype_enemy_bucket.elo = calc_elo(bucket.elo, subtype_enemy_bucket.elo)
        else:
            bucket.elo, new_elo = calc_elo(bucket.elo, subtype_enemy_bucket.elo)
            delta_elo = new_elo - subtype_enemy_bucket.elo  # This is negative!
            # This elo will be touched twice: once in subtype, once in not-filtered type.
            # Hence take (approximately) the average delta.
            subtype_enemy_bucket.elo += round(delta_elo / 2)
    else:  # Enemy has subtypes
        enemy_bucket_key = (bucket.tour, shotdown_enemy[0], bucket.NO_FILTER)
        enemy_bucket = ensure_bucket_in_cache(cache_enemy_buckets, enemy_bucket_key, None)

        if has_subtype:
            if is_subtype:
                bucket.elo, subtype_enemy_bucket.elo = calc_elo(bucket.elo, enemy_bucket.elo)
            else:
                bucket.elo, enemy_bucket.elo = calc_elo(bucket.elo, enemy_bucket.elo)
        else:
            first_new_elo, enemy_bucket.elo = calc_elo(bucket.elo, enemy_bucket.elo)
            second_new_elo, subtype_enemy_bucket.elo = calc_elo(bucket.elo, subtype_enemy_bucket.elo)

            first_delta_elo = first_new_elo - bucket.elo
            second_delta_elo = second_new_elo - bucket.elo
            bucket.elo = round(bucket.elo + first_delta_elo / 2 + second_delta_elo / 2)


def ensure_bucket_in_cache(cache_enemy_buckets, bucket_key, player):
    if bucket_key not in cache_enemy_buckets:
        cache_enemy_buckets[bucket_key] = (AircraftBucket.objects.get_or_create(
            tour=bucket_key[0], aircraft=bucket_key[1], filter_type=bucket_key[2], player=player))[0]

    return cache_enemy_buckets[bucket_key]


def update_damaged_enemy(bucket, damaged_enemy, enemies_killed, enemies_shotdown, enemy_sortie, kb,
                         update_primary_bucket):
    if kb.aircraft_1.aircraft == bucket.aircraft:
        kb.aircraft_1_distinct_hits += 1
        if update_primary_bucket:
            bucket.distinct_enemies_hit += 1
        if enemy_sortie.is_shotdown:
            if update_primary_bucket:
                bucket.plane_lethality_counter += 1
            if damaged_enemy not in enemies_shotdown:
                kb.aircraft_1_assists += 1

        if enemy_sortie.is_dead:
            if update_primary_bucket:
                bucket.pilot_lethality_counter += 1
            if damaged_enemy not in enemies_killed:
                kb.aircraft_1_pk_assists += 1
    else:
        kb.aircraft_2_distinct_hits += 1
        if update_primary_bucket:
            bucket.distinct_enemies_hit += 1
        if enemy_sortie.is_shotdown:
            bucket.plane_lethality_counter += 1
            if damaged_enemy not in enemies_shotdown:
                kb.aircraft_2_assists += 1

        if enemy_sortie.is_dead:
            if update_primary_bucket:
                bucket.pilot_lethality_counter += 1
            if damaged_enemy not in enemies_killed:
                kb.aircraft_2_pk_assists += 1


def process_aa_accident_death(bucket, sortie):
    if not sortie.is_lost_aircraft:
        return

    types_damaged = list((LogEntry.objects
                          .values_list('act_object__cls', flat=True)
                          .filter(Q(type='shotdown') | Q(type='killed') | Q(type='destroyed'), cact_sortie=sortie)
                          .order_by().distinct()))

    if len(types_damaged) == 0 or (len(types_damaged) == 1 and types_damaged[0] is None):
        bucket.aircraft_lost_to_accident += 1
        bucket.deaths_to_accident += 1 if sortie.is_relive else 0
    else:
        only_aa = True
        for type_damaged in types_damaged:
            if type_damaged and 'aa' not in type_damaged:
                only_aa = False

        if only_aa:
            bucket.aircraft_lost_to_aa += 1
            bucket.deaths_to_aa += 1 if sortie.is_relive else 0


def process_ammo_breakdown(bucket, sortie, is_subtype):
    # We only care about statistics like "avg shots to kill" or "avg shots till our plane lost".
    if not sortie.is_lost_aircraft:
        return

    # We only process Sorties where there was essentially a single source of damage.
    # Note: Planes also take damage when crashing into the ground. We ignore these sources of damage.
    # So to be more precise, we only want damage from exactly a single enemy aircraft/AA/Tank/object type.
    # I.e. "Only took damage from a Spitfire Mk IX" or "Only took damage from a Flak 88".
    if not sortie.ammo['ammo_breakdown']['dmg_from_one_source']:
        return

    enemy_objects = (LogEntry.objects
                     .values_list('act_object', 'act_sortie')
                     .filter(Q(cact_sortie_id=sortie.id),
                             Q(type='shotdown') | Q(type='killed') | Q(type='damaged'),
                             Q(act_object__cls_base='aircraft') | Q(act_object__cls_base='vehicle')
                             | Q(act_object__cls__contains='tank') | Q(act_object__cls_base='turret'),
                             # Disregard Sorties flown by AI
                             cact_sortie_id__isnull=False)
                     # Disregard sorties shotdown by AI plane.
                     .exclude(Q(act_object__cls_base='aircraft') & Q(act_sortie_id__isnull=True))
                     .order_by().distinct())

    if enemy_objects.count() != 1:
        if enemy_objects.count() > 1 and sortie.ammo['ammo_breakdown']['last_turret_account'] is not None:
            # We've been hit by a turret!
            # Check if we've been hit by multiple turrets of the same plane.
            # If so, continue - otherwise there is a bug in the sortie log where we throw out the data.
            # I.e. we got hit by an aircraft turret and the MGs of another plane (the MGs didn't cause any dmg)
            aircraft_hit_us = set()
            for enemy_object in enemy_objects:
                db_enemy_object = Object.objects.get(id=enemy_object[0])
                if db_enemy_object.cls != 'aircraft_turret':
                    return
                aircraft = turret_to_aircraft_bucket(db_enemy_object.name, db_enemy_object.log_name, tour=bucket.tour)
                if aircraft is None:
                    return
                aircraft_hit_us.add(aircraft.id)
                if len(aircraft_hit_us) != 1:
                    return

        else:
            return
            # Something went wrong here. This is likely due to errors in the sortie logs.
            # I.e. "Damage" and "Hits" ATypes tell a different story.
            # According to "Hits", there should be one source of damage, according to "Damage" that isn't the case.
            # (Likely) Because the hits were so minor that they didn't register as damage.
            # Just in case, we're still throwing the data out, there will be more than enough left over.
    ammo_breakdown = sortie.ammo['ammo_breakdown']

    # TODO: At some point make this less hacky. Possibly derive other ammo from aircraft payload?
    # This is a totally band-aid solution.
    # The Tempest and spitfire destroys targets often in a single gun cycle, so the other Hispano ammo doesn't show up
    # in the ammo breakdown. This pollutes the data, especially since it happens often.
    # So we manually add in the missing ammo type (HE or AP).
    fill_in_ammo(ammo_breakdown, 'SHELL_ENG_20x110_AP', 'SHELL_ENG_20x110_HE')
    # Same problem as above, but for MG 151/20 and MG 151/15.
    fill_in_ammo(ammo_breakdown, 'SHELL_GER_20x82_AP', 'SHELL_GER_20x82_HE')
    fill_in_ammo(ammo_breakdown, 'SHELL_GER_15x96_AP', 'SHELL_GER_15x96_HE')

    # For ShVAKs: We keep it as is, since LA-5(FN) has mono-ammo belts.
    # So even if another plane has a fluke like this, it does same damage as when shot by LA-5 anyways.

    enemy_object = enemy_objects[0][0]
    enemy_sortie = enemy_objects[0][1]
    db_enemy_object = Object.objects.get(id=enemy_object)
    pilot_snipe = is_pilot_snipe(sortie)

    bucket.increment_ammo_received(ammo_breakdown['total_received'], pilot_snipe)
    if not bucket.player:
        write_breakdown_line(bucket, ammo_breakdown['total_received'], DEFENSIVE_BREAKDOWN, db_enemy_object,
                             pilot_snipe)

    if is_subtype:
        # Updates for enemy aircraft were done in main type.
        return

    if db_enemy_object.cls_base != 'aircraft' and db_enemy_object.cls != 'aircraft_turret':
        return
    if db_enemy_object.cls_base == 'aircraft' and not enemy_sortie:
        return

    base_bucket, db_sortie, filtered_bucket = ammo_breakdown_enemy_bucket(ammo_breakdown, bucket, db_enemy_object,
                                                                          enemy_sortie)

    if base_bucket is not None:
        base_bucket.increment_ammo_given(ammo_breakdown['total_received'], pilot_snipe)
        if not base_bucket.player:
            write_breakdown_line(base_bucket, ammo_breakdown['total_received'], OFFENSIVE_BREAKDOWN, bucket.aircraft,
                                 pilot_snipe)
        base_bucket.save()
    if filtered_bucket is not None:
        filtered_bucket.increment_ammo_given(ammo_breakdown['total_received'], pilot_snipe)
        if not filtered_bucket.player:
            write_breakdown_line(filtered_bucket, ammo_breakdown['total_received'], OFFENSIVE_BREAKDOWN,
                                 bucket.aircraft, pilot_snipe)
        filtered_bucket.save()


def fill_in_ammo(ammo_breakdown, ap_ammo, he_ammo):
    if (ap_ammo not in ammo_breakdown['total_received']
            and he_ammo in ammo_breakdown['total_received']):
        ammo_breakdown['total_received'][ap_ammo] = 0
    if (he_ammo not in ammo_breakdown['total_received']
            and ap_ammo in ammo_breakdown['total_received']):
        ammo_breakdown['total_received'][he_ammo] = 0


def is_pilot_snipe(sortie):
    """
    A pilot snipe is when a plane goes down because the pilot gets killed, and not because the aircraft is crtically
    damaged. Currently, in the logs, a pilot snipe looks rather similar to a normal death. Even in a pilot snipe,
    the logs think the aircraft gets shotdown before the pilot dies - i.e. it emits "plane shotdown" before "pilot dead"

    Instead the logs sees to relay the information that it was a pilot snipe by "damage to the pilot". I.e. a pilot
    snipe has "damage to pilot X by plane Y" events, whereas a death due to a not pilot snipe has "damgage to pilot X
    without a plane" events.

    So, to check for pilot snipe we check:

    1. The pilot must have died to a player/AI object.
    2. That the death didn't happen much later than the shotdown, otherwise it could've been someone strafing a plane
    which was already dead.
    3. That the shotdown didn't happen much later than the last damage to pilot event, otherwise it could be as above.
    4. That there was sufficent damage to the pilot from enemy planes to cause a death to the pilot.

    If all 4 conditions are satisified, then it's a pilot snipe.
    """
    death_event = (LogEntry.objects
                   .filter(Q(cact_sortie_id=sortie.id),
                           Q(type='killed'), act_object_id__isnull=False))

    shotdown_event = (LogEntry.objects
                      .filter(Q(cact_sortie_id=sortie.id),
                              Q(type='killed'), act_object_id__isnull=False))

    wound_events = (LogEntry.objects
                    .filter(Q(cact_sortie_id=sortie.id),
                            Q(type='wounded'), act_object_id__isnull=False)
                    .order_by('-tik'))

    if not death_event.exists() or not shotdown_event.exists() or not wound_events.exists():
        # Condition 1 in function description.
        return False

    death_event = death_event[0]
    shotdown_event = shotdown_event[0]

    if death_event.tik - shotdown_event.tik > 20:
        # Condition 2 in function description
        # Threshold is 20 tiks = 0.4 seconds.
        return False

    if wound_events[0].tik - shotdown_event.tik > 20:
        # Condition 3 in function description.
        # Threshold is 20 tiks = 0.4 seconds.
        return False

    wound_damage = 0
    for wound_event in wound_events:
        if type(wound_event.extra_data['damage']) is dict:
            wound_damage += wound_event.extra_data['damage']['pct']
        else:
            wound_damage += wound_event.extra_data['damage']

    return wound_damage > 0.95  # Condition 4 in function description. At least 95% damage threshold.


def ammo_breakdown_enemy_bucket(ammo_breakdown, bucket, db_object, enemy_sortie):
    """
    This finds the bucket which damaged our plane for ammo breakdown purposes.

    There are two main cases: We've been damaged by the main guns of an aircraft, and we've been damaged by the turret.
    Unfortunately, it is impossible to find the Sortie corresponding to the aircraft turret, which results in divergent
    logic.

    @param ammo_breakdown The ammo breakdown of our sortie.
    @param bucket Our bucket, i.e. the plane which got damaged.
    @param db_object The object which did the damaging. May be an aircraft or turret.
    @param enemy_sortie None if turret (can't know sortie), otherwise the id of Sortie of the plane which damaged our plane.

    @return base_bucket: Enemy bucket who did the damaging,
            db_sortie: Sortie corresponding to input enemy_sortie or None if not passed.
            filtered_bucket: Enemy subbucket which did the damaging, e.g. "With bombs" if jabo flight.
    """
    if db_object.cls_base == 'aircraft':
        db_sortie = Sortie.objects.get(id=enemy_sortie)
        if bucket.player:  # We only want to update the enemy player bucket and the enemy generic bucket once each.
            base_bucket = AircraftBucket.objects.get_or_create(
                tour=db_sortie.tour, aircraft=db_object, filter_type='NO_FILTER', player=db_sortie.player)[0]
        else:
            base_bucket = AircraftBucket.objects.get_or_create(
                tour=db_sortie.tour, aircraft=db_object, filter_type='NO_FILTER', player=None)[0]

        filter_type = get_sortie_type(db_sortie)
        if filter_type != 'NO_FILTER' and db_sortie.player:
            if bucket.player:  # We only want to update the enemy player bucket and the enemy generic bucket once each.
                filtered_bucket = AircraftBucket.objects.get_or_create(
                    tour=bucket.tour, aircraft=db_object, filter_type=filter_type, player=db_sortie.player)[0]
            else:
                filtered_bucket = AircraftBucket.objects.get_or_create(
                    tour=bucket.tour, aircraft=db_object, filter_type=filter_type, player=None)[0]
        else:
            filtered_bucket = None

    else:  # Turret
        db_sortie = None
        # Note that we can't update filtered Halberstadt (turreted plane with jabo type)
        # here since we don't know which subtype it is.
        filtered_bucket = None
        if bucket.player:  # We only want to update the enemy player bucket and the enemy generic bucket once each.
            if 'last_turret_account' in ammo_breakdown:
                try:
                    enemy_player = Player.objects.filter(
                        profile__uuid=ammo_breakdown['last_turret_account'],
                        tour=bucket.tour,
                        type='pilot'
                    ).get()
                    base_bucket = turret_to_aircraft_bucket(db_object.name, db_object.log_name, tour=bucket.tour,
                                                            player=enemy_player)
                except Player.DoesNotExist:
                    base_bucket = None
            else:
                base_bucket = None
        else:
            base_bucket = turret_to_aircraft_bucket(db_object.name, db_object.log_name, tour=bucket.tour)
    return base_bucket, db_sortie, filtered_bucket


def process_streaks_and_best_sorties(bucket, sortie):
    """
    Updates fields like max_score_streak, current_ak_streak, and best_score_in_sortie.

    This method may update the passed bucket, but also the bucket without player.

    @param bucket Player bucket associated to sortie. This is one of the buckets that may be updated.
    @param sortie Sortie which is being processed now.
    """

    bucket.current_score_streak += sortie.score
    bucket.current_ak_streak += sortie.ak_total
    if IGNORE_AI_KILLS_STREAKS:
        killboard = sortie.killboard_pve
        aircraft_types = ['aircraft_light', 'aircraft_medium', 'aircraft_heavy', 'aircraft_transport']
        for aircraft_type in aircraft_types:
            bucket.current_ak_streak -= killboard[aircraft_type] if aircraft_type in killboard else 0
    bucket.current_gk_streak += sortie.gk_total

    bucket.max_score_streak = max(bucket.max_score_streak, bucket.current_score_streak)
    bucket.max_ak_streak = max(bucket.max_ak_streak, bucket.current_ak_streak)
    bucket.max_gk_streak = max(bucket.max_gk_streak, bucket.current_gk_streak)

    if sortie.score > bucket.best_score_in_sortie:
        bucket.best_score_in_sortie = sortie.score
        bucket.best_score_sortie = sortie
    if sortie.ak_total > bucket.best_ak_in_sortie:
        bucket.best_ak_in_sortie = sortie.ak_total
        bucket.best_ak_sortie = sortie
    if sortie.gk_total > bucket.best_gk_in_sortie:
        bucket.best_gk_in_sortie = sortie.gk_total
        bucket.best_gk_sortie = sortie

    if sortie.is_relive:
        bucket.current_score_streak = 0
        bucket.current_ak_streak = 0
        bucket.current_gk_streak = 0

    not_player_bucket = AircraftBucket.objects.filter(
        tour=sortie.tour,
        aircraft=sortie.aircraft,
        filter_type=bucket.filter_type,
        player=None,
    ).get_or_create()[0]

    if bucket.max_score_streak > not_player_bucket.max_score_streak:
        not_player_bucket.max_score_streak = bucket.max_score_streak
        not_player_bucket.max_score_streak_player = sortie.player
    if bucket.max_ak_streak > not_player_bucket.max_ak_streak:
        not_player_bucket.max_ak_streak = bucket.max_ak_streak
        not_player_bucket.max_ak_streak_player = sortie.player
    if bucket.max_gk_streak > not_player_bucket.max_gk_streak:
        not_player_bucket.max_gk_streak = bucket.max_gk_streak
        not_player_bucket.max_gk_streak_player = sortie.player

    if sortie.score > not_player_bucket.best_score_in_sortie:
        not_player_bucket.best_score_in_sortie = sortie.score
        not_player_bucket.best_score_sortie = sortie
    if sortie.ak_total > not_player_bucket.best_ak_in_sortie:
        not_player_bucket.best_ak_in_sortie = sortie.ak_total
        not_player_bucket.best_ak_sortie = sortie
    if sortie.gk_total > not_player_bucket.best_gk_in_sortie:
        not_player_bucket.best_gk_in_sortie = sortie.gk_total
        not_player_bucket.best_gk_sortie = sortie

    sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.computed_max_streaks = True
    sortie.SortieAugmentation_MOD_STATS_BY_AIRCRAFT.save()

    not_player_bucket.save()


def get_killboards(enemy, bucket, cache_kb, cache_enemy_buckets_kb, use_pilot_kbs, update_primary_bucket):
    (enemy_aircraft, enemy_sortie) = enemy

    enemy_bucket_keys = set()
    if update_primary_bucket:
        # This is the case where we are updating only a bucket with a Player, from the perspective of the turret.
        # The values of the turret's aircraft bucket should not change, only the damaged Player's bucket.
        enemy_bucket_keys.add((bucket.tour, enemy_aircraft, bucket.NO_FILTER, None))
    if use_pilot_kbs:
        # This happens when the bucket doesn't have a player, in this case we record "Player in aircraft X got damaged"
        # Or in the case where we're looking from the perspective of the turret, then this happens in the case
        # that we're currently updating a player bucket, here we record "player in aircrafct X got damaged by turret"
        enemy_bucket_keys.add((bucket.tour, enemy_aircraft, bucket.NO_FILTER, enemy_sortie.player))
    if has_bomb_variant(enemy_aircraft) or has_juiced_variant(enemy_aircraft):
        if update_primary_bucket:
            # This is the case where we are updating only a bucket with a Player, from the perspective of the turret.
            # The values of the turret's aircraft bucket should not change, only the damaged Player's bucket.
            enemy_bucket_keys.add((bucket.tour, enemy_aircraft, get_sortie_type(enemy_sortie), None))
        if use_pilot_kbs:
            # This happens when the bucket doesn't have a player, in this case we record "Player in aircraft X got damaged"
            # Or in the case where we're looking from the perspective of the turret, then this happens in the case
            # that we're currently updating a player bucket, here we record "player in aircrafct X got damaged by turret"
            enemy_bucket_keys.add((bucket.tour, enemy_aircraft, get_sortie_type(enemy_sortie), enemy_sortie.player))

    result = []
    for enemy_bucket_key in enemy_bucket_keys:
        if enemy_bucket_key in cache_enemy_buckets_kb:
            enemy_bucket = cache_enemy_buckets_kb[enemy_bucket_key]
        else:
            (enemy_bucket, created) = AircraftBucket.objects.get_or_create(
                tour=enemy_bucket_key[0], aircraft=enemy_bucket_key[1], filter_type=enemy_bucket_key[2],
                player=enemy_bucket_key[3])
            cache_enemy_buckets_kb[enemy_bucket_key] = enemy_bucket
            if created:
                enemy_bucket.update_derived_fields()
                enemy_bucket.save()

        if bucket.id < enemy_bucket.id:
            kb_key = (bucket, enemy_bucket)
        else:
            kb_key = (enemy_bucket, bucket)

        if kb_key not in cache_kb:
            kb = (AircraftKillboard.objects.get_or_create(aircraft_1=kb_key[0], aircraft_2=kb_key[1],
                                                          tour=bucket.tour))[0]
            cache_kb[kb_key] = kb
        result.append(cache_kb[kb_key])

    return result


def calc_elo(winner_rating, loser_rating):
    """
    From https://github.com/ddm7018/Elo
    """
    k = 15  # Low k factor (in chess ~30 is common), because there will be a lot of engagements.
    # k factor is the largest amount elo can shift. So a plane gains/loses at most k = 15 per engagement.
    result = expected_result(winner_rating, loser_rating)
    new_winner_rating = winner_rating + k * (1 - result)
    new_loser_rating = loser_rating + k * (0 - (1 - result))
    return int(round(new_winner_rating)), int(round(new_loser_rating))


def expected_result(p1, p2):
    exp = (p2 - p1) / 400.0
    return 1 / ((10.0 ** exp) + 1)


TURRET_AMBIGUITIES = {
    'Bristol',
    'Halberstadt'
}

TURRET_TO_AIRCRAFT = {
    'turretbristolf2b_1': 'Bristol F2B (F.II)',
    'turretbristolf2bf2_1': 'Bristol F2B (F.II)',
    'turretbristolf2bf2_1_wm2': 'Bristol F2B (F.II)',
    'turretbristolf2bf2_1m': 'Bristol F2B (F.II)',
    'turretbristolf2bf3_1': 'Bristol F2B (F.III)',
    'turretbristolf2bf3_1_wm2': 'Bristol F2B (F.III)',
    'turretbristolf2bf3_1m': 'Bristol F2B (F.III)',
    'turrethalberstadtcl2_1': 'Halberstadt CL.II',
    'turrethalberstadtcl2_1_wm_beckap': 'Halberstadt CL.II',
    'turrethalberstadtcl2_1_wm_beckhe': 'Halberstadt CL.II',
    'turrethalberstadtcl2_1_wm_beckheap': 'Halberstadt CL.II',
    'turrethalberstadtcl2_1_wm_twinpar': 'Halberstadt CL.II',
    'turrethalberstadtcl2_1m': 'Halberstadt CL.II',
    'turrethalberstadtcl2_1m2': 'Halberstadt CL.II',
    'turrethalberstadtcl2au_1': 'Halberstadt CL.II 200hp',
    'turrethalberstadtcl2au_1_wm_beckap': 'Halberstadt CL.II 200hp',
    'turrethalberstadtcl2au_1_wm_beckhe': 'Halberstadt CL.II 200hp',
    'turrethalberstadtcl2au_1_wm_beckheap': 'Halberstadt CL.II 200hp',
    'turrethalberstadtcl2au_1_wm_twinpar': 'Halberstadt CL.II 200hp',
    'turrethalberstadtcl2au_1m': 'Halberstadt CL.II 200hp',
    'turrethalberstadtcl2au_1m2': 'Halberstadt CL.II 200hp',
}

TYPOS = {
    'Airco DH4': 'Airco D.H.4',
    'U-2VS': 'U-﻿2',
}


def turret_to_aircraft_bucket(turret_name, log_name, tour, player=None):
    aircraft_name = turret_name[:len(turret_name) - 7]
    if aircraft_name in TYPOS:
        aircraft_name = TYPOS[aircraft_name]
    if aircraft_name in TURRET_AMBIGUITIES:
        aircraft_name = TURRET_TO_AIRCRAFT[log_name]

    if 'B25' in aircraft_name:
        # It's an AI flight, which isn't (yet) supported.
        return None
    try:
        aircraft = Object.objects.filter(name=aircraft_name).get()
        return (AircraftBucket.objects.get_or_create(tour=tour, aircraft=aircraft, filter_type='NO_FILTER',
                                                     player=player))[0]
    except Object.DoesNotExist:
        logger.warning("[mod_stats_by_aircraft] Could not find aircraft for turret " + turret_name)
        return None

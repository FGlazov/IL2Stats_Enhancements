from .config_modules import MODULE_AMMO_BREAKDOWN, module_active

TOTAL_HITS = 'total_hits'
TOTAL_RECEIVED = 'total_received'
ALL_TAKEN = 'all_taken'
DMG_FROM_ONE_SOURCE = 'dmg_from_one_source'
LAST_DMG_SORTIE = 'last_dmg_sortie'
LAST_DMG_OBJECT = 'last_dmg_object'
LAST_TURRET_ACCOUNT = 'last_turret_account'


def event_hit(self, tik, ammo, attacker_id, target_id):
    # ======================== MODDED PART BEGIN
    ammo_db = self.objects[ammo.lower()]
    # ======================== MODDED PART END

    ammo = self.objects[ammo.lower()]['cls']
    attacker = self.get_object(object_id=attacker_id)
    target = self.get_object(object_id=target_id)
    if target:
        target.got_hit(ammo=ammo, attacker=attacker)
        # ======================== MODDED PART BEGIN
        record_hits(target, attacker, ammo_db)
        # ======================== MODDED PART END


# ======================== MODDED PART BEGIN
def record_hits(target, attacker, ammo):
    if not module_active(MODULE_AMMO_BREAKDOWN):
        return

    if ammo['cls'] != 'shell' and ammo['cls'] != 'bullet':
        return

    if target.sortie:
        if not hasattr(target.sortie, 'ammo_breakdown'):
            target.sortie.ammo_breakdown = default_ammo_breakdown()

        increment(target.sortie.ammo_breakdown, TOTAL_RECEIVED, ammo['name'])
        target.sortie.ammo_breakdown[ALL_TAKEN] += 1

        if attacker:
            ammo_breakdown = target.sortie.ammo_breakdown
            if ammo_breakdown[LAST_DMG_OBJECT] is None and ammo_breakdown[LAST_DMG_SORTIE] is None:
                ammo_breakdown[DMG_FROM_ONE_SOURCE] = True
            else:
                if attacker.sortie and attacker.sortie.index != ammo_breakdown[LAST_DMG_SORTIE]:
                    ammo_breakdown[DMG_FROM_ONE_SOURCE] = False
                if attacker.id != target.sortie.ammo_breakdown[LAST_DMG_OBJECT]:
                    ammo_breakdown[DMG_FROM_ONE_SOURCE] = False

            ammo_breakdown[LAST_DMG_OBJECT] = attacker.id
            if attacker.sortie:
                ammo_breakdown[LAST_DMG_SORTIE] = attacker.sortie.index

            if attacker.cls == 'aircraft_turret' and attacker.parent:
                ammo_breakdown[LAST_TURRET_ACCOUNT] = attacker.parent.sortie.account_id

    if attacker and attacker.coal_id == target.coal_id:
        return

    sortie = attacker.sortie
    if attacker.cls == 'aircraft_turret' and attacker.parent:
        sortie = attacker.parent.sortie

    if sortie:
        if not hasattr(sortie, 'ammo_breakdown'):
            sortie.ammo_breakdown = default_ammo_breakdown()

        increment(sortie.ammo_breakdown, TOTAL_HITS, ammo['name'])


def default_ammo_breakdown():
    return {
        TOTAL_HITS: dict(),
        TOTAL_RECEIVED: dict(),
        ALL_TAKEN: 0,
        DMG_FROM_ONE_SOURCE: False,
        LAST_DMG_SORTIE: None,
        LAST_DMG_OBJECT: None,
    }


def increment(ammo_breakdown, main_key, subkey):
    if subkey in ammo_breakdown[main_key]:
        ammo_breakdown[main_key][subkey] += 1
    else:
        ammo_breakdown[main_key][subkey] = 1


def encode_tuple(obj, ammo):
    return str(obj.id) + ":" + ammo['log_name']


def decode_to_tuple(encoded):
    split = encoded.split(':')
    object_id = split[0]
    ammo_log_name = split[1]
    return object_id, ammo_log_name
# ======================== MODDED PART END

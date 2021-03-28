HIT_BY_OBJECT = 'hit_by_object'
RECEIVED_BY_OBJECT = 'received_by_object'
TOTAL_HITS = 'total_hits'
TOTAL_RECEIVED = 'total_received'


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
    # TODO: Create the Modules system. Modularize SplitRankings.
    # TODO: Don't compute this if module is not active.

    if ammo['cls'] != 'shell' and ammo['cls'] != 'bullet':
        return

    if target.sortie:
        if not hasattr(target.sortie, 'ammo_breakdown'):
            target.sortie.ammo_breakdown = default_ammo_breakdown()

        increment(target.sortie.ammo_breakdown, TOTAL_RECEIVED, ammo['log_name'])
        increment(target.sortie.ammo_breakdown, RECEIVED_BY_OBJECT, encode_tuple(target, ammo))

    if attacker and attacker.sortie:
        if not hasattr(attacker.sortie, 'ammo_breakdown'):
            attacker.sortie.ammo_breakdown = default_ammo_breakdown()

        increment(attacker.sortie.ammo_breakdown, TOTAL_HITS, ammo['log_name'])
        increment(attacker.sortie.ammo_breakdown, HIT_BY_OBJECT, encode_tuple(target, ammo))


def default_ammo_breakdown():
    return {
        HIT_BY_OBJECT: dict(),
        RECEIVED_BY_OBJECT: dict(),
        TOTAL_HITS: dict(),
        TOTAL_RECEIVED: dict(),
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

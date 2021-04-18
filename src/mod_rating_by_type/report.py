from .config_modules import MODULE_AMMO_BREAKDOWN, module_active

TOTAL_HITS = 'total_hits'
TOTAL_RECEIVED = 'total_received'
ALL_TAKEN = 'all_taken'
DMG_FROM_ONE_SOURCE = 'dmg_from_one_source'
LAST_DMG_SORTIE = 'last_dmg_sortie'
LAST_DMG_OBJECT = 'last_dmg_object'
LAST_TURRET_ACCOUNT = 'last_turret_account'


class RecentHitsCache:
    def __init__(self):
        self.cache = {}
        self.prune_counter = 0

    def add_to_hits_cache(self, tik, target, attacker, ammo):
        if target is None or attacker is None:
            return

        if target.parent:
            target = target.parent
        if attacker.parent:
            attacker = attacker.parent

        key = (target.id, attacker.id)

        if key not in self.cache:
            self.cache[key] = []

        self.cache[key].append({'ammo': ammo['name'], 'tik': tik})

        self.prune_counter += 1
        if self.prune_counter > PRUNE_COUNTER_MAX:
            self.prune_hits_cache(tik)

    def prune_hits_cache(self, current_tik):
        empty_keys = []
        for key in self.cache:
            self.cache[key] = [hit for hit in self.cache[key] if current_tik - hit['tik'] < RECENT_HITS_CUTOFF]
            if not self.cache[key]:
                empty_keys.append(key)

        for empty_key in empty_keys:
            del self.cache[empty_key]

        self.prune_counter = 0

    def get_recent_hits(self, current_tik, attacker, target):
        if target is None or attacker is None:
            return {}

        if target.parent:
            target = target.parent
        if attacker.parent:
            attacker = attacker.parent

        key = (target.id, attacker.id)
        if key not in self.cache:
            return {}

        recent_hits = [hit for hit in self.cache[key] if current_tik - hit['tik'] < RECENT_HITS_CUTOFF]
        result = {}
        for recent_hit in recent_hits:
            ammo = recent_hit['ammo']
            if ammo not in result:
                result[ammo] = 0
            result[ammo] += 1

        return result


RECENT_HITS_CACHE = RecentHitsCache()
RECENT_HITS_CUTOFF = 250  # After 250 ticks = ~5 seconds a hit isn't considered recent anymore.
PRUNE_COUNTER_MAX = 500  # After 500 event hits prune the cache.


# Monkey patched event_hit in report.py
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
        record_hits(tik, target, attacker, ammo_db)
        # ======================== MODDED PART END


# Monkey patched event_damage in report.py.
def event_damage(self, tik, damage, attacker_id, target_id, pos):
    attacker = self.get_object(object_id=attacker_id)
    target = self.get_object(object_id=target_id)
    # дамага может не быть из-за бага логов
    if target and damage:
        # таймаут для парашютистов
        if target.sortie and target.is_crew() and target.sortie.is_ended_by_timeout(timeout=120, tik=tik):
            return
        if target.sortie and not target.is_crew() and target.sortie.is_ended:
            return
        # ======================== MODDED PART BEGIN (pass tik)
        target.got_damaged(damage=damage, attacker=attacker, pos=pos, tik=tik)
        # ======================== MODDED PART END


# Monkey patched into Object class inside report.py
def got_damaged(self, damage, tik, attacker=None, pos=None):
    """
    :type damage: int | float
    :type attacker: Object | None
    """
    if self.life_status.is_destroyed:
        return
    self.life_status.damage()
    self.damage += damage
    # если атакуем сами себя - убираем прямое упоминание об этом
    if self.is_attack_itself(attacker=attacker):
        attacker = None
    if attacker:
        self.damagers[attacker] += damage
    is_friendly_fire = True if attacker and attacker.coal_id == self.coal_id else False

    # ======================== MODDED PART BEGIN
    self.mission.logger_event({
        'type': 'damage',
        'damage': damage,
        'pos': pos,
        'attacker': attacker,
        'target': self,
        'is_friendly_fire': is_friendly_fire,
        'hits': RECENT_HITS_CACHE.get_recent_hits(tik, attacker, self)
    })
    # ======================== MODDED PART END


# ======================== MODDED PART BEGIN
def record_hits(tik, target, attacker, ammo):
    if not module_active(MODULE_AMMO_BREAKDOWN):
        return

    if ammo['cls'] != 'shell' and ammo['cls'] != 'bullet':
        return

    RECENT_HITS_CACHE.add_to_hits_cache(tik, target, attacker, ammo)

    sortie = target.sortie
    if target.parent:
        sortie = target.parent.sortie

    if sortie:
        if not hasattr(sortie, 'ammo_breakdown'):
            sortie.ammo_breakdown = default_ammo_breakdown()

        increment(sortie.ammo_breakdown, TOTAL_RECEIVED, ammo['name'])
        sortie.ammo_breakdown[ALL_TAKEN] += 1

        if attacker:
            attacker_id = attacker.id
            if attacker.cls == 'aircraft_turret' and attacker.parent and attacker.parent.sortie:
                # Multiple turrets of an aircraft are counted together!
                # That's why we take the aircraft's sortie.
                attacker_id = attacker.parent.sortie.index

            ammo_breakdown = sortie.ammo_breakdown
            if ammo_breakdown[LAST_DMG_OBJECT] is None and ammo_breakdown[LAST_DMG_SORTIE] is None:
                ammo_breakdown[DMG_FROM_ONE_SOURCE] = True
            else:
                if attacker.sortie and attacker.sortie.index != ammo_breakdown[LAST_DMG_SORTIE]:
                    ammo_breakdown[DMG_FROM_ONE_SOURCE] = False
                if attacker_id != sortie.ammo_breakdown[LAST_DMG_OBJECT]:
                    ammo_breakdown[DMG_FROM_ONE_SOURCE] = False

            ammo_breakdown[LAST_DMG_OBJECT] = attacker_id
            if attacker.sortie:
                ammo_breakdown[LAST_DMG_SORTIE] = attacker.sortie.index

            if attacker.cls == 'aircraft_turret' and attacker.parent:
                ammo_breakdown[LAST_TURRET_ACCOUNT] = attacker.parent.sortie.account_id

    if attacker and attacker.coal_id == target.coal_id:
        return

    sortie = attacker.sortie
    if attacker.parent:
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
        LAST_TURRET_ACCOUNT: None,
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

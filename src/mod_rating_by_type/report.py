from .config_modules import MODULE_AMMO_BREAKDOWN, MODULE_REARM_ACCURACY_WORKAROUND, \
    MODULE_BAILOUT_ACCURACY_WORKAROUND, module_active
import operator

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

# Monkey patched into Object class inside report.py
def got_damaged(self, damage, attacker=None, pos=None):
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
        'damage': {
            'pct': damage,
            'hits': RECENT_HITS_CACHE.get_recent_hits(self.mission.tik_last, attacker, self)
        },
        'pos': pos,
        'attacker': attacker,
        'target': self,
        'is_friendly_fire': is_friendly_fire,
    })
    # ======================== MODDED PART END


# Monkey patched into Object class inside report.py
def takeoff(self, tik):
    self.is_takeoff = True
    self.on_ground = False
    self.is_rtb = False
    self.uncaptured()
    if self.sortie:
        self.sortie.tik_landed = None
        if not self.sortie.tik_takeoff:
            self.sortie.tik_takeoff = tik

    # ======================== MODDED PART BEGIN
    if not module_active(MODULE_REARM_ACCURACY_WORKAROUND):
        return
    # If you rearm then your number of shots gets reset to 0. This screws up gunnery accuracy.
    # So we use "taking off twice" as a proxy for rearming, since there is no rearm event.
    if not hasattr(self, 'takeoff_count'):
        self.takeoff_count = 0
    self.takeoff_count += 1
    # ======================== MODDED PART END


# Monkey patched into Object class inside report.py
def got_killed(self, attacker=None, pos=None, force_by_dmg=False):
    """
    :type attacker: Object | None
    """
    if self.is_killed:
        # TODO добавить логирование
        return

    self.life_status.destroy()
    # дамагеры отсортированные по величине дамага
    damagers = [a[0] for a in sorted(self.damagers.items(), key=operator.itemgetter(1), reverse=True)]
    if attacker:
        if attacker in damagers:
            damagers.remove(attacker)
            damagers.insert(0, attacker)
    # если убийца не известен - вычисляем убийцу по повреждениям
    else:
        # если атакующий не известен и цель самолет в полете -
        # откладываем принятие решения на потом (земля, прыжок и т.п.)
        if not force_by_dmg and (self.cls_base == 'aircraft' and not self.on_ground):
            return
        if damagers:
            attacker = damagers[0]

    # если атакуем сами себя - убираем прямое упоминание об этом
    if self.is_attack_itself(attacker=attacker):
        attacker = None

    is_friendly_fire = True if attacker and attacker.coal_id == self.coal_id else False

    if attacker:
        self.is_killed = True
        self.killers = damagers
        attacker.killboard[self.cls].add(self)
        # добавляем второго по величине дамага в ассисты (если надамагал больше 1%)
        if len(damagers) > 1 and self.damagers[damagers[1]] > 1:
            damagers[1].assistboard[self.cls].add(self)
        # зачет киллов от турелей и т.п.
        # не передавать киллы пилоту, если за стрелка был игрок и был убит союзный объект
        if attacker.parent and not (attacker.sortie and is_friendly_fire):
            attacker.parent.killboard[self.cls].add(self)
            # ======================== MODDED PART BEGIN
            if self.cls_base == 'aircraft':
                if not hasattr(attacker.parent, "turret_kills"):
                    attacker.parent.turret_kills = set()
                attacker.parent.turret_kills.add(self)
            # ======================== MODDED PART END
    # если есть убийца, или это игровое событие - пишем в лог
    if attacker or not force_by_dmg:
        self.mission.logger_event({'type': 'kill', 'attacker': attacker, 'pos': pos,
                                   'target': self, 'is_friendly_fire': is_friendly_fire})


# ======================== MODDED PART BEGIN
def record_hits(target, attacker, ammo):
    if not module_active(MODULE_AMMO_BREAKDOWN):
        return

    if ammo['cls'] != 'shell' and ammo['cls'] != 'bullet':
        return

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

            if attacker.cls == 'aircraft_turret' and attacker.parent and attacker.parent.sortie:
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

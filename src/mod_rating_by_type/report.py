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
def record_hits(target, attacker, ammo_db):
    # TODO: Create the Modules system. Modularize SplitRankings.
    # TODO: Don't compute this if module is not active.
    print("Recording hits!")
    pass
# ======================== MODDED PART END


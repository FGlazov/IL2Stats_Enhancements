============================================
IL-2 Stats Enhancements
============================================
Authors: =FEW=Revolves and Enigma89

This is a mod for IL2 Stats, which adds and changes minor things to the IL2 stats websites. The mod is seperated into modules, which can be turned on and off so you can customize which of the features of the mod you wish to use. Descriptions of the modules follow.

This version of the mod is compatible with version 1.2.50 of IL2 stats.

------------ Modules which show new information ------------ 

----------------------------
Module Split Rankings
----------------------------

Config name: split_rankings

This module's main goal is to visualize who is the best fighter, attacker, and bomber pilot/squad. To that aim, it introduces seperate personas for fighter, attacker and bomber planes, similar to how pilots and squads are already ranked in the original version of IL2 stats. You can now check your rating in fighter planes, or, for example, your ground kills per hour in attacker flights only.

The wonderful IL2 Stats website has been created by =FB=Vaal and =FB=Isaay. We thank =FB=Vaal and =FB=Isaay for helping us create this module. We also thank X51 Vaudoo, botya, SamVimes, and an unnamed Spanish speaking volunteer (They never let us know who they were!) for their help translating this module. We also thank RaptorAttacker for his graphic work for helping us make the icons.

Video introduction: https://www.youtube.com/watch?v=5NU9jxvSP30

DISCLAIMER: This module is NOT (currently) retroactive, it will only split the stats of new sorties. 

----------------------------
Module Ammo Breakdown
----------------------------

Config name: ammo_breakdown

This module modifies the sortie views to show how many and which bullets you've taken in that sortie. E.g. you can now see you've taken 30 hits in an IL-2 that one sortie, 20 of which were MG 17, and another 10 MG 151/20 hits. Additionally, you can also see which bullets you've hit, e.g.. you can see how many cannon rounds and MG rounds you hit. The idea is you can use this mod to analyze how hits many you can take without going down, or judging whether you're perhaps only hitting with MG rounds and whiffing all your cannon rounds.

If you additionally have the Global Aircraft Stats mod, then you will also be able to see Average Ammo To kill/Average ammo to death statistics. For example, you could see the average number of ShVAK rounds needed to take down a BF 109 G-4. 

Thanks to PR9INICHEK, HawkerMkIII, =FEW=Hauggy, Arkanno, JorgeHFJ and GhostDragon for providing translations!


DISCLAIMER: This module is not retroactive, and will likely never be. It only gives you ammo breakdowns of new sorties. This also applies to the Global Aircraft Stats mod, the average offensive/defensive breakdowns of ammo can only be computed on new sorties.

----------------------------
Module Ironman Stats
----------------------------

Config name: ironman_stats

This module adds a new table "Ironman Rankings" to IL2 stats, which is similar to the Pilot Rankings. The difference is that the stats in this page get reset as soon as your pilot dies. This is essentially an overview of all the current virutal lives. For past tours, the table instead shows the best streak of each pilot.

Thanks to PR9INICHEK, HawkerMkIII and =FEW=Hauggy, Arkanno, JorgeHFJ and GhostDragon for helping us translate this module!

---------------------------
Module Top Last Mission
---------------------------

Config name: top_last_mission 

This module replaces the "Top players in last 24 hours" with "Top players in last mission" on the main page of the website. This is compatible with the split rankings module. This module is mainly meant for servers which do not run 24/7, such as weekly event servers.

Thanks to HawkerMkIII, PR9INICHEK, JorgeHFJ, and =FEW=Hauggy, Arkanno, JorgeHFJ and GhostDragon for providing translations!

------------ Modules changing scoring of sorties ------------ 

All of these scoring modules do NOT apply retroactively. They only apply to sorties after the module has been activated.

----------------------------
Module Adjustable Bonuses and Penalties.
----------------------------
Config name: adjustable_bonuses_penalties

This module gives you more control over the basic modifiers which affect a sortie's score. In the base version of IL2 Stats, you receive a 25% bonus for landing your plane, and a 25% bonus for being on the winning side of a mission. These are not adjustable in the base version, and there are no penalities for dying/getting captured/bailing out/getting shotdown.

This module adds penalties for dying/getting captured/bailing out/getting shotdown, as well as a bonus for being "In Flight" (i.e. server ended map without you landing). All of these bonuses and penalties are adjustable. To adjust the values, login into your IL2 Stats website as an admin, and go to the admin panel. Under Stats->Scoring you'll find the following variables, which you can give custom values (0% is a perfectly acceptable value!):

Config name              | Default
-------------------------|--------
mod_bonus_landed         | 100%
mod_bonus_winning_coal   | 25%
mod_bonus_in_flight      | 100%
mod_penalty_dead         | 75%
mod_penalty_captured     | 75%
mod_penalty_bailout      | 50%
mod_penalty_shotdown     | 20%


Thanks to PR9INICHEK, HawkerMkIII, =FEW=Hauggy, Arkanno, JorgeHFJ and GhostDragon for providing translations.


----------------------------
Module Flight Time Bonus
----------------------------

Config name: flight_time_bonus

This module adds bonus points to sorties depending on how long the player stayed in the air. By default, 1 minute results in 1 bonus point. The point of this scoring change is to encourge people to run CAP over areas which do not see much action, as sometimes you may have sorties where there simply is no action. 

If you wish to change the rate at which players gain points for staying in the air, then login into your IL2 stats installation as an admin. In the Admin Panel, under Stats->Scoring you will find the variable "mod_flight_time_bonus". By default it is 60, which stands for the 60 seconds a player needs to stay in the air in order to receive a point. 

Thanks to PR9INICHEK, HawkerMkIII, =FEW=Hauggy, Arkanno, JorgeHFJ and GhostDragon for their work translating this module!

----------------------------
Module Undamaged Bailout Penalty
----------------------------

Config name: undamaged_bailout_penalty

This module adds a penalty to sorties where the player bailed out of their aircraft without having any damage taken. By default, the player loses (up to, score can't be negative) 100 points and 20 fairplay points if he bails out of an undamaged plane with this module enabled. The idea here is to encourge people to fight, instead of bailing out at the first sign of trouble to deny a kill or in order to preserve your kill streak. If you take any damage before bailout, then this does not apply.

If you wish to change the concrete values for this penalty, then login into your IL2 stats installation as an admin. In the Admin Panel, under Stats->Scoring you will find the two variables "mod_undmg_bailout_score" and "mod_undmg_bailout_fair". The first variable is how many points are taken away as penalty, and the second variable controls the number of fairplay points that are taken away. Set a custom value for those variables you wish to change.

Thanks to PR9INICHEK, HawkerMkIII, =FEW=Hauggy, Arkanno, JorgeHFJ and GhostDragon for providing translations.


----------------------------
Module Mission Win New Tour
----------------------------

Config name: mission_win_new_tour

This module makes IL2 stats start a new tour every time a mission is won. This is primarily meant for servers which have few mission wins, where a win is for example the result of a long dynamic campaign spanning several days or even weeks. 

------------ Modules for bug workarounds ------------ 

----------------------------
Module Rearm Accuracy
----------------------------

Config name: rearm_accuracy_workaround
 
There is a bug in the IL-2 server logs which results in the number of bullets you shot to be reset whenever you rearm your plane without ending the sortie. Unforutanetely, there is no way to extract how many bullets you shot before the rearm. This leads to sorties where a player can somehow hit more bullets than you shot, for example: https://imgur.com/qo2YDH9

The concern here is that while we can't fix the data, we can prevent this data from counting towards player accuracy. The base version of IL-2 stats currently does not count sorties where the number of hits exceeded the number of shots towards accuracy. This module provides yet another work around - if a player takes off twice, then that sortie is also not counted towards gunner accuracy. Currently, there is no way to detect a rearm event. Since you need to land to rearm, any sortie where you rearm has at least two takeoffs, and this module thus prevents those sorties from being counted towards accuracy.

DISCLAIMER: This module is not retroactive, and will likely never be.

----------------------------
Module Bailout Accuracy
----------------------------

Config name: bailout_accuracy_workaround

There is a bug in the IL-2 server logs where the number of remaining bullets you have in your plane is counted as 0 when you bailout, this essentialy means the logs think that you shoot out your entire arsenal when you bail out. This means you end up with sorties with very low gunnery accuracy, since you did not actually shot that many bullets. This module prevents bailout sorties from counting towards a pilot's accuracy. An example of this kind of sortie: https://imgur.com/ZgpY6un

DISCLAIMER: This module is not retroactive, and will likely never be.

Installation
---------------------------------------------

1. You need an installation of il2 stats. The latest version can be found under https://forum.il2sturmovik.com/topic/19083-il2-stats-statistics-system-for-a-dedicated-server-il2-battle-of-stalingrad/

2. Copy the src folder inside this .zip into your il2 stats folder.

3. Inside your src/conf.ini add the line "mods = mod_rating_by_type" under [stats]. If you have multiple mods, you can separate them as "mods = mod1, mod_rating_by_type". As an example, you might have the following lines under [stats].

4. Inside your src/conf.ini add the config parameter modules under [stats]. Set it to the modules you want using their config names, seperated by commas. For example, if you want the Split Ranking and Ammo Breakdown modules, you need to add the line "modules = split_rankings, ammo_breakdown". 

After step 3 and 4 your config should contain two lines like:

mods = mod_rating_by_type
modules = split_rankings, ammo_breakdown, ironman_stats

4a. If you're using the split rankings module: It is possible to retroactively compute the fighter/attacker/bomber personas for already existing misisons before this mod was installed. The config paramater is called "retro_compute_for_last_tours=10" under [stats] in src/conf.ini. It is shared with the global aircraft stats mod. A value of 0 will retroactively compute for only the current tour (for any sorties in the current tour before this mod was installed), a value of -1 will completely disable the retroactive computations. The default value of 10 retroactively aggregates stats for the previous 10 tours and the current one.

5. Run update.cmd in your run folder.

Uninstallation
---------------------------------------------
Remove mod_rating_by_type from mods in your src/conf.ini.
If you want to also remove the unused mod files, then you can delete the folder src/mod_rating_by_type

Support
---------------------------------------------
Contact =FEW=Revolves on the IL2 forums.


Compatibility with other mods
---------------------------------------------


This mod is compatible with Global Aircraft Stats. Make sure mod_stats_by_aircraft comes after mod_rating_by_type in the mods config parameter. I.e., like:
mods = mod_rating_by_type, mod_stats_by_aircraft

This mod is incompatible with the disconnect mod, consider perhaps using the mod bundle:  https://forum.il2sturmovik.com/topic/70029-il-2-stats-mod-bundle-disco-tanks-splitrankings/ - (and remove the tank rankings from the src/mod_stats_by_aircraft/base.html if you don't have tanks) . 

This mod is incompatible with the tank mod.

If you want to run all four mods at the same time, consider this bundle: https://forum.il2sturmovik.com/topic/70029-il-2-stats-mod-bundle-disco-tanks-splitrankings/

License
---------------------------------------------
The mod is licensed under the MIT License.

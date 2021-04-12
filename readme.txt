============================================
IL-2 Stats Enhancements
============================================
Authors: =FEW=Revolves and Enigma89

This is a mod for IL2 Stats, which adds and changes minor things to the IL2 stats websites. The mod is seperated into modules, which can be turned on and off so you can customize which of the features of the mod you wish to use. Descriptions of the modules follow.

This version of the mod is compatible with version 1.2.49 of IL2 stats.

----------------------------
Module Split Rankings
----------------------------

Config name: split_rankings

This module's main goal is to visualize who is the best fighter, attacker, and bomber pilot/squad. To that aim, it introduces rankings for fighter, attacker and bomber planes, similar to how pilots and squads are already ranked in the original version of IL2 stats. New fields include, for example, "Top fighter pilot in the last 24 hours" and "Best bomber streak".

The wonderful IL2 Stats website has been created by =FB=Vaal and =FB=Isaay. We thank =FB=Vaal and =FB=Isaay for helping us create this module. We also thank X51 Vaudoo, botya, SamVimes, and an unnamed Spanish speaking volunteer (They never let us know who they were!) for their help translating this module. We also thank RaptorAttacker for his graphic work for helping us make the icons.

Video introduction: https://www.youtube.com/watch?v=5NU9jxvSP30

DISCLAIMER: This module is NOT (currently) retroactive, it will only split the stats of new sorties. 

----------------------------
Module Ammo Breakdown
----------------------------

Config name: ammo_breakdown

This module modifies the sortie views to show how many and which bullets you've taken in that sortie. E.g. you can now see you've taken 30 hits in an IL-2 that one sortie, 20 of which were MG 17, and another 10 MG 151/20 hits. Additionally, you can also see which bullets you've hit, e.g.. you can see how many cannon rounds and MG rounds you hit. The idea is you can use this mod to analyze how hits many you can take without going down, or judging whether you're perhaps only hitting with MG rounds and whiffing all your cannon rounds.

If you additionally have the Global Aircraft Stats mod, then you will also be able to see Average Ammo To kill/Average ammo to death statistics. For example, you could see the average number of ShVAK rounds needed to take down a BF 109 G-4. 

Thanks to PR9INICHEK, HawkerMkIII and =FEW=Hauggy for translating this module into Russian, Spanish, and French respectively. 


DISCLAIMER: This module is not retroactive, and will likely never be. It only gives you ammo breakdowns of new sorties. This also applies to the Global Aircraft Stats mod, the average offensive/defensive breakdowns of ammo can only be computed on new sorties.

----------------------------
Module Ironman Stats
----------------------------

Config name: ironman_stats

This module adds a new table "Ironman Rankings" to IL2 stats, which is similar to the Pilot Rankings. The difference is that the stats in this page get reset as soon as your pilot dies. This is essentially an overview of all the current virutal lives. For past tours, the table instead shows the best streak of each pilot.

Thanks to PR9INICHEK, HawkerMkIII and =FEW=Hauggy for translating this module into Russian, Spanish, and French respectively. 

 
Installation
---------------------------------------------

1. You need an installation of il2 stats. The latest version can be found under https://forum.il2sturmovik.com/topic/19083-il2-stats-statistics-system-for-a-dedicated-server-il2-battle-of-stalingrad/

2. Copy the src folder inside this .zip into your il2 stats folder.

3. Inside your src/conf.ini add the line "mods = mod_rating_by_type" under [stats]. If you have multiple mods, you can separate them as "mods = mod1, mod_rating_by_type". As an example, you might have the following lines under [stats].

4. Inside your src/conf.ini add the config parameter modules under [stats]. Set it to the modules you want using their config names, seperated by commas. For example, if you want the Split Ranking and Ammo Breakdown modules, you need to add the line "modules = split_rankings, ammo_breakdown". 

After step 3 and 4 your config should contain two lines like:

mods = mod_rating_by_type
modules = split_rankings, ammo_breakdown, ironman_stats

5. Run collect_static in your run folder. Otherwise you will likely get a 500 error on the pilot rankings page.

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

This mod is incompatible with the disconnect mod, but a compatbility patch is included in the .zip. After installing both mods, copy over the src file in the compatbility_patch/disconnect folder. Made for version 1.6 of the disconnect mod.

This mod is incompatible with the tank mod.

If you want to run all four mods at the same time, consider this bundle: https://forum.il2sturmovik.com/topic/70029-il-2-stats-mod-bundle-disco-tanks-splitrankings/

License
---------------------------------------------
The mod is licensed under the MIT License.

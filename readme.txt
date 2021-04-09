<<<<<<< HEAD
============================================================================
IL-2 Stats Mod Bundle: Disco + Tanks + SplitRankings + Global Aircraft Stats
============================================================================
Bundle compiled by: =FEW=Revolves

This is a IL-2 stats mod compilation consisting of three mods:

Tank mod by CountZero ( https://forum.il2sturmovik.com/topic/55657-mod-to-add-tank-missions-for-il2-stats-system-made-by-fbvaal-and-fbisay/ )
Disconnect mod by CountZero ( https://forum.il2sturmovik.com/topic/56709-mod-for-il2-stats-system-more-options-for-disconnection-situations/ )
Split Rankings mod by =Few=Revolves and Enigma89 ( https://forum.il2sturmovik.com/topic/69965-il-2-stats-submod-split-rankings/ )
Global Aircraft Stats mod =Few=Revolves and Enigma89  ( https://forum.il2sturmovik.com/topic/70380-il-2-stats-mod-global-aircraft-stats/ )
=======
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
>>>>>>> master

IL-2 stats is a website designed by =FB=Vaal and and =FB=Islay, which is used to track statistics on most IL-2 dedicated
servers.

<<<<<<< HEAD
This bundle version is designed to work with version 1.2.48 of IL-2 stats.

Disconnect mod version: 1.5
Tank mod version: 2.9.1
Split Rankings mod version : 1.1.0
Global Aircraft Stats mod version : 1.0.2

Note that if you wish to run the disconnect mod and split ranking mod together (without tanks), you don't need any
special bundle! The two mods are compatible as is, just install both of them over each other. Global Aircraft Stats
also works well with the other mods, see its readme.
=======
DISCLAIMER: This module is NOT (currently) retroactive, it will only split the stats of new sorties. 

----------------------------
Module Ammo Breakdown
----------------------------

Config name: ammo_breakdown

This module modifies the sortie views to show how many and which bullets you've taken in that sortie. E.g. you can now see you've taken 30 hits in an IL-2 that one sortie, 20 of which were MG 17, and another 10 MG 151/20 hits. Additionally, you can also see which bullets you've hit, e.g.. you can see how many cannon rounds and MG rounds you hit. The idea is you can use this mod to analyze how hits many you can take without going down, or judging whether you're perhaps only hitting with MG rounds and whiffing all your cannon rounds.

If you additionally have the Global Aircraft Stats mod, then you will also be able to see Average Ammo To kill/Average ammo to death statistics. For example, you could see the average number of ShVAK rounds needed to take down a BF 109 G-4. 

Thanks to PR9INICHEK, HawkerMkIII and =FEW=Hauggy for translating this module into Russian, Spanish, and French respectively. 

3. Inside your src/conf.ini, change the "mods" parameter under [stats] to "mods=mod_rating_by_type, mod_stats_by_aircraft".
If you don't have such a parameter, then add it. 

4. Inside your src/conf.ini, configure the disconnect mod as you desire. To be precise, you need to add the lines
sortie_disco_min_time = 0
sortie_damage_disco_time = 120
under [stats], with values as you wish (in seconds).
More details in the disconnect mod thread/readme.

5. Inside your src/conf.ini, configure how many tours back you wish to retroactively compute for the global aircraft stats mod.
The parameter is "retro_compute_for_last_tours=10" under [stats]. A value of -1 disables retroactive computations,
0 retroactively computes for all sorties inside the current tour (before the mod was installed). A value of 10 computes for
the last 10 tours. More details inside the Global Aircraft stats readme.

3. Inside your src/conf.ini add the line "mods = mod_rating_by_type" under [stats]. If you have multiple mods, you can separate them as "mods = mod1, mod_rating_by_type". As an example, you might have the following lines under [stats].

4. Inside your src/conf.ini add the config parameter modules under [stats]. Set it to the modules you want using their config names, seperated by commas. For example, if you want the Split Ranking and Ammo Breakdown modules, you need to add the line "modules = split_rankings, ammo_breakdown". 

5. Run collect_static in your run folder. Otherwise you will likely get a 500 error on the pilot rankings page.

6. Run the update script in your /run folder after you're done with the above.

Support
---------------------------------------------
Contact =FEW=Revolves on the IL2 forums.


Compatibility with other mods
---------------------------------------------

This mod bundle is unlikely to be compatible with any other mod, since it touches most of the files.

License
---------------------------------------------
The mod bundle is licensed under the MIT License.

=================================================================================
IL-2 Stats Mod Bundle: Disco + Tanks + Stats Enhancements + Global Aircraft Stats
=================================================================================
Bundle compiled by: =FEW=Revolves

This is a IL-2 stats mod compilation consisting of three mods:

Tank mod by CountZero ( https://forum.il2sturmovik.com/topic/55657-mod-to-add-tank-missions-for-il2-stats-system-made-by-fbvaal-and-fbisay/ )
Disconnect mod by CountZero ( https://forum.il2sturmovik.com/topic/56709-mod-for-il2-stats-system-more-options-for-disconnection-situations/ )
Split Rankings mod by =Few=Revolves and Enigma89 ( https://forum.il2sturmovik.com/topic/69965-il-2-stats-submod-split-rankings/ )
Global Aircraft Stats mod =Few=Revolves and Enigma89  ( https://forum.il2sturmovik.com/topic/70380-il-2-stats-mod-global-aircraft-stats/ )

This bundle version is designed to work with version 1.2.64 of IL-2 stats.

Disconnect mod version: 1.7
Tank mod version: 3.5
Stats Enhancements version : 2.4.2
Global Aircraft Stats mod version : 1.5.0

Installation
--------------------------------------------
1. You need an installation of il2 stats. The latest version can be found under https://forum.il2sturmovik.com/topic/19083-il2-stats-statistics-system-for-a-dedicated-server-il2-battle-of-stalingrad/

2. Copy the src folder inside this .zip into your il2 stats folder.

3. Inside your src/conf.ini, change the "mods" parameter under [stats] to "mods=mod_rating_by_type, mod_stats_by_aircraft".
If you don't have such a parameter, then add it. 

4. Inside your src/conf.ini, configure the disconnect mod as you desire. To be precise, you need to add the lines
sortie_disco_min_time = 0
sortie_damage_disco_time = 120
under [stats], with values as you wish (in seconds).
More details in the disconnect mod thread/readme.

5. Inside your src/conf.ini, configure how many tours back you wish to retroactively compute for the global aircraft stats mod and split rankings module.
The parameter is "retro_compute_for_last_tours=10" under [stats]. A value of -1 disables retroactive computations,
0 retroactively computes for all sorties inside the current tour (before the mod was installed). A value of 10 computes for
the last 10 tours. More details inside the Global Aircraft stats readme.

6. Inside your src/conf.ini, configure the  Stats Enhancements mod. I.e. choose the modules you want to use with the config parameter "modules" under [stats]. List of config modules can be found here: https://forum.il2sturmovik.com/topic/69965-il-2-stats-mod-enhancements/ (alternatively inside the readme of the il2 stats enchancments mod, can be downloaded in the link above as well)

If, for example, you want to use modules "Split rankings", "Ammo breakdown" and "Flight time bonus" you would write:

modules=split_rankings, ammo_breakdown, adjustable_bonuses_penalties

7. Run the update script in your /run folder after you're done with the above.

8. If you're using the module "Adjustable Bonuses and Penalities", there are seperate variables for tank bonuses/penalties you might wish to configure. You can find them inside the admin panel under "Scoring".

Config name              | Default
-------------------------|--------
tank_bonus_landed        | 100%
tank_bonus_winning_coa   | 25%
tank_bonus_in_flight     | 100%
tank_bonus_in_service    | 100%
tank_penalty_dead        | 75%
tank_penalty_captured    | 75%
tank_penalty_bailout     | 50%
tank_penalty_shotdown    | 20%

Currently "in_service" is the scenario where a tank makes it back, "in_flight" or "landed" might become relevant if the game logs change. 

Support
---------------------------------------------
Contact =FEW=Revolves on the IL2 forums.


Compatibility with other mods
---------------------------------------------

This mod bundle is unlikely to be compatible with any other mod, since it touches most of the files.

License
---------------------------------------------
The mod bundle is licensed under the MIT License.

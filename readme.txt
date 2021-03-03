============================================
IL-2 Stats Submod: Split Rankings
============================================
Authors: =FEW=Revolves and Enigma89

This is a mod which adds more information to your IL2 Stats website. Its main goal is to visualize who is the best fighter, attacker, and bomber pilot/squad. To that aim, it introduces rankings for fighter, attacker and bomber planes, similar to how pilots and squads are already ranked in the original version of IL2 stats. New fields include, for example, "Top fighter pilot in the last 24 hours" and "Best bomber streak".

The wonderful IL2 Stats website has been created by =FB=Vaal and =FB=Isaay. We thank =FB=Vaal and =FB=Isaay for helping us create this mod. We also thank X51 Vaudoo, botya, SamVimes, and an unnamed Spanish speaking volunteer (They never let us know who they were!) for their help translating this mod. We also thank RaptorAttacker for his graphic work for helping us make the icons.

Video introduction: https://www.youtube.com/watch?v=5NU9jxvSP30

This version is compatible with 1.2.48 of IL2 stats.

DISCLAIMER: This mod is NOT (currently) retroactive, it will only split the stats of new sorties. 

Installation
---------------------------------------------

1. You need an installation of il2 stats. The latest version can be found under https://forum.il2sturmovik.com/topic/19083-il2-stats-statistics-system-for-a-dedicated-server-il2-battle-of-stalingrad/

2. Copy the src folder inside this .zip into your il2 stats folder.

3. Inside your src/conf.ini, add the line "mods = mod_rating_by_type" under [stats]. If you have multiple mods, you can separate them as "mods = mod1, mod_rating_by_type". As an example, you might have the following lines under [stats].

[stats]
mission_report_delete = false
mission_report_backup_days = 31
inactive_player_days = 331
new_tour_by_month = true
win_by_score = true
win_score_min = 2000
win_score_ratio = 1.25
sortie_min_time = 0
skin_id = 1
mods = mod_rating_by_type

Uninstallation
---------------------------------------------
Remove mod_rating_by_type from mods in your src/conf.ini.
If you want to also remove the unused mod files, then you can delete the folder src/mod_rating_by_type

Support
---------------------------------------------
Contact =FEW=Revolves on the IL2 forums.


Compatibility with other mods
---------------------------------------------

This mod modifies the following files. If another mod also modifies these files, there is a high chance that this mod will not be compatible with the other mod without some work.

src/stats/views.py
src/stats/urls.py
src/stats/templates/tour.html
src/stats/templates/squad_pilots.html
src/stats/templates/squads.html
src/stats/templates/squad.html
src/stats/templates/pilots.html
src/stats/templates/pilot.html
src/stats/templates/mission.html
src/stats/templates/main.html
src/stats/locale/ru/LC_MESSAGES/* (all files in this dir)
src/stats/locale/fr/LC_MESSAGES/* (all files in this dir)
src/stats/locale/es/LC_MESSAGES/* (all files in this dir)
src/stats/locale/de/LC_MESSAGES/* (all files in this dir)

If these two mods are incompatible, then you may attempt to merge the changes together. Most friendly python programmers will be able to do this quickly! If you're technically minded, you can attempt to do this even without programming knowledge. If you don't know any friendly programmers, you may contact =FEW=Revolves on the forums and I'll try to get back to you and Frankenstein your two mods together.


License
---------------------------------------------
The mod is licensed under the MIT License.

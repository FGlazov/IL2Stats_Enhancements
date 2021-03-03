====================================================
IL-2 Stats Mod Bundle: Disco + Tanks + SplitRankings
====================================================
Bundle compiled by: =FEW=Revolves

This is a IL-2 stats mod compilation consisting of three mods:

Tank mod by CountZero ( https://forum.il2sturmovik.com/topic/55657-mod-to-add-tank-missions-for-il2-stats-system-made-by-fbvaal-and-fbisay/ )
Disconnect mod by CountZero ( https://forum.il2sturmovik.com/topic/56709-mod-for-il2-stats-system-more-options-for-disconnection-situations/ )
Split Rankings mod by =Few=Revolves and Enigma89 ( https://forum.il2sturmovik.com/topic/69965-il-2-stats-submod-split-rankings/ )

IL-2 stats is a website designed by =FB=Vaal and and =FB=Islay, which is used to track statistics on most IL-2 dedicated
servers.

This bundle version is designed to work with version 1.2.48 of IL-2 stats.

Disconnect mod version: 1.5
Tank mod version: 2.9
Split Rankings mod version : 1.0.1

Note that if you wish to run the disconnect mod and split ranking mod together (without tanks), you don't need any
special bundle! The two mods are compatible as is, just install both of them over each other.

Installation
---------------------------------------------

1. You need an installation of il2 stats. The latest version can be found under https://forum.il2sturmovik.com/topic/19083-il2-stats-statistics-system-for-a-dedicated-server-il2-battle-of-stalingrad/

2. Copy the src folder inside this .zip into your il2 stats folder.

3. Inside your src/conf.ini, add the line "mods = mod_rating_by_type" under [stats].

4. Inside your src/conf ini, configure the disconnect mod as you desire. To be precise, you need to add the lines
sortie_disco_min_time = 0
sortie_damage_disco_time = 120
under [stats], with values as you wish (in seconds).

5. Run the collect_static script in your /run folder after you're done with the above.

Support
---------------------------------------------
Contact =FEW=Revolves on the IL2 forums.


Compatibility with other mods
---------------------------------------------

This mod bundle is unlikely to be compatible with any other mod, since it touches most of the files.

License
---------------------------------------------
The mod bundle is licensed under the MIT License.

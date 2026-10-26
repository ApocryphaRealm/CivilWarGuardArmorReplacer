# Civil War Guard Armor Replacer

Version 2.0.0 (this build's own number; the source mods' versions are their own).

One install covering both sides of the Civil War and the hold guards:

* **Sons of Skyrim** ([68656](https://www.nexusmods.com/skyrimspecialedition/mods/68656)) - the
  Stormcloak and hold-guard armour, by NordwarUA.
* **New Legion** ([30468](https://www.nexusmods.com/skyrimspecialedition/mods/30468)) - the Imperial
  Legion replacer, by NordwarUA. Its two dragon-motif sets - the officer armour and the emperor's - were
  removed on 2026-09-18: General Tullius wears the Imperial Tribune set instead, the Civil War officers wear
  the Legate cuirass with the Legate helmet, and Titus Mede II wears New Legion's ordinary Imperial armour.
* **Guards Armor Replacer** ([22671](https://www.nexusmods.com/skyrimspecialedition/mods/22671)) -
  its Winterhold set and its Windhelm Scale set, light and heavy, standing in for Sons of Skyrim's
  own versions of those two holds.
* **Imperial Tribune Armor** ([54294](https://www.nexusmods.com/skyrimspecialedition/mods/54294)) by
  Gypsymama, with General Tullius wearing it.

**Requires Spell Perk Item Distributor 7.2 or later** ([36869](https://www.nexusmods.com/skyrimspecialedition/mods/36869)).

**SPID dresses the guards; the plugin only defines the armour.** `Civil War Guard Armor Replacer_DISTR.ini`
hands the outfits out at runtime - to the NPCs 1.0.x gave a particular variant, by name, and to whoever the
plugins dress in a vanilla guard or soldier outfit, by that outfit - so no NPC, outfit, quest, cell or dialogue
record is edited, and an NPC who never wore a guard outfit (a Vigilant of Stendarr, a bandit) cannot be
re-dressed. It works on existing saves. SPID cannot create records, so one light plugin
(`Civil War Guard Armor Replacer.esp`, ESPFE) still holds the armour, weapons, outfits and recipes themselves.
`docs/spid-design.md` explains the split; `tools/spid-convert.py` builds both files and `tools/verify-spid.py`
checks them against a Mod Organizer 2 load order. `docs/plugin-merge-analysis.md` records how the plugin was
first merged from the source mods.

None of the art is ours. The build scripts read the Nexus downloads at build time; this repository
carries no meshes, textures or plugins belonging to anyone else.

## Licence

Our scripts and documentation are GPL-3.0-or-later, Copyright (C) 2026 ApocryphaRealm. The armour is
its authors' - see `NOTICE.md`.

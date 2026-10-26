# Civil War Guard Armor Replacer - changelog

## 2.0.0 - 2026-10-26 - untested

### Changed
- **Who wears what is now decided by Spell Perk Item Distributor, not by the plugin.** The plugin only defines the
  armour; `Civil War Guard Armor Replacer_DISTR.ini` hands it out. Section B names the NPCs 1.0.x gave a particular
  variant (259 NPCs, each paired with the outfit it starts in); section A gives whoever the plugins dress in a vanilla
  guard / soldier outfit this mod's version of it (58 lines). The vanilla outfit is the filter, so the rules reach
  exactly the NPCs 1.0.x reached - a Vigilant of Stendarr, bandit or citizen cannot match. Works on existing saves.
- The plugin keeps its name and every FormID, stays light, and holds item records only: the new armour, weapons and
  their first-person models, the outfits and levelled lists, crafting recipes, and the vanilla Imperial / Penitus /
  Stormcloak pieces whose art it replaces. 71 new `CWGAR_` outfits and levelled lists carry what 1.0.x wrote into
  vanilla outfits and lists, so the vanilla records are no longer edited. 956 records (was 1312).
- Built by `tools/spid-convert.py` from the 1.0.1 plugin; `tools/verify-spid.py` proves it against a load order
  (Njordlinger Test: 0 unresolved forms, 815 NPCs dressed, nobody gained or lost this mod's armour, 40 NPCs in another
  variant of the same set, 78 Vigilants of Stendarr unchanged). Design: `docs/spid-design.md`.

### Added
- Requirement: Spell Perk Item Distributor 7.2 or later.

### Removed
- The 264 NPC record edits (with Sons of Skyrim's inventory, stat, class and name changes - guards carry vanilla
  weapons again), the 45 vanilla outfit and 28 levelled list edits, the levelled guard lists, blacksmith stock, the
  Civil War and Dark Brotherhood quest edits, the armour displays in Dragonsreach, the Jarl's Longhouse, the Palace of
  the Kings and Helgen Keep (the vanilla clutter they deleted returns), and five guard dialogue lines. SPID cannot
  carry placed objects or dialogue, and none of them is a guard's armour.

### Fixed (carried from the withdrawn, never-posted 1.0.1 - the regrouped plugin is the input spid-convert reads; 2.0.0 then removes its placed references and dialogue)
- **The plugin's records sit in the groups the game and Mutagen read them from.** The merged plugin carried
  top-level REFR and INFO groups and held its four cell edits loose in the CELL group, because the merge tool
  kept each source's records but dropped the group tree that says which cell a placed object is in and which
  topic a dialogue response belongs to. Mutagen refused the file ("Read in data that was not a GRUP"), so any
  Synthesis patcher that reads every group failed on it, and the engine could not place those records.
  - The 65 placed references go back into their cells' children groups: Dragonsreach Jarl's Quarters (14),
    the Jarl's Longhouse in Winterhold (7), the Palace of the Kings (39) - Sons of Skyrim's armour displays and
    the vanilla clutter it removes - and Helgen Keep (5, New Legion's rusted Legion armour set).
  - The five guard dialogue responses go back under their two topics.
  - Nothing else changed: the other 1242 records are byte-identical, and no FormID moved, so saves are unaffected.
  - Repaired in place with `.MD\scripts\plugins\esp-regroup.py` (role `esp-regroup`), because the plugin was
    edited after the merge and re-merging would have discarded those edits:
    `esp-regroup.py "Civil War Guard Armor Replacer.esp.bak-before-regroup-20261025" --out "Civil War Guard Armor Replacer.esp" --parents-from "<Sons of Skyrim>\NW_Sons_of_Skyrim.esp" --assign 0x5000AF3-0x5000AF7=0x5DE24`
    (Sons of Skyrim places 60 of the references and all five responses; the five Helgen pieces come from New
    Legion, whose plugin is not on this machine, and their positions fall inside Helgen Keep's vanilla bounds).
  - Verified: Mutagen 0.54.4 reads all 1312 records in both its import and overlay modes (1.0.0: overlay refused,
    import silently dropped 74), and esp-audit passes for runtime 1.5.97.
- `merge-to-espfe.py` now writes the full group tree itself, so a re-merge cannot reintroduce this.

### Fixed
- Four item names were misspelled: 'Windhelm Ligth Helmet' and two 'Stormcloak Ligth Shield' now read 'Light', and 'General Tullius' Cermonial Sword' reads 'Ceremonial' (found by the 2.0.0 in-game test; every FULL name in the plugin was scanned). spid-convert.py fixes them in the kept records (NAME_FIXES); a record diff against the previous build shows only those four FULL strings changed - same 956 records, FormIDs, order, flags and masters - and the _DISTR.ini and verify-spid.py output are identical. EditorIDs keep their old spelling.

## 1.0.0 - 2026-09-17

- Sons of Skyrim, New Legion, Guards Armor Replacer's Winterhold and Windhelm Scale sets and the Imperial Tribune
  armour as one install behind one merged light plugin (`docs/plugin-merge-analysis.md`). Later in-place edits
  (2026-09-18 to 21): New Legion's dragon-motif sets removed, Civil War officers in the Legate set, shield swap,
  Stormcloak heavy set, Windhelm patrol.

# Civil War Guard Armor Replacer - changelog

## 1.0.1 - 2026-10-25 - untested

### Fixed
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

## 1.0.0 - 2026-09-17

- Sons of Skyrim, New Legion, Guards Armor Replacer's Winterhold and Windhelm Scale sets and the Imperial Tribune
  armour as one install behind one merged light plugin (`docs/plugin-merge-analysis.md`). Later in-place edits
  (2026-09-18 to 21): New Legion's dragon-motif sets removed, Civil War officers in the Legate set, shield swap,
  Stormcloak heavy set, Windhelm patrol.

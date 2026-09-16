# Merging four plugins into one ESL - what the sources actually contain

Written 2026-09-16, before any merge code was run, so the build starts from measurements rather
than assumptions. Everything below was read out of the plugin files themselves.

The owner's instruction: *"I want to decompile all the ESPs or ESLs from these other mods and make
a, one, a single unified ESL for our all-in-one mod."*

## The four sources

| Plugin | Mod | New records | Overrides | ESL now | Masters |
|---|---|---|---|---|---|
| `NW_Sons_of_Skyrim.esp` | Sons of Skyrim (68656) | 667 | 304 | no | Skyrim, Update, Dawnguard, HearthFires, Dragonborn |
| `DIS_Heavy_Legion.esp` | New Legion (30468) | 184 | 97 | no | Skyrim, Update |
| `TribuneArmor.esp` (ESL edition) | Imperial Tribune Armor (54294) | 42 | 0 | **yes** | Skyrim, Dawnguard, Dragonborn |
| `ImperialTribuneTulliusReplacer.esp` | same mod, optional file | 21 | 4 | no | all five |

**893 new records** if the Tullius replacer's duplicate armour is dropped (see below). A light
plugin has 2048 new-record slots, `0x000800`-`0x000FFF`, so the merge lands around 44% full.
Overrides do not consume slots.

The merged plugin's masters are the union: Skyrim, Update, Dawnguard, HearthFires, Dragonborn.

## The merge is unusually clean - three collisions, and they are the ones we want

Every override was reduced to a canonical `(master file, local id)` pair and compared across all
four plugins:

* **Sons of Skyrim and New Legion overlap on nothing.** Not one shared record. They divide cleanly
  into the Stormcloak/hold-guard half and the Imperial half.
* **The Tribune ESL overrides nothing at all** - it is pure new content.
* **New Legion and the Tullius outfit replacer collide on exactly three records:**
  * `Skyrim.esm:05CBFE` - `GeneralTulliusArmor` (ARMO)
  * `Skyrim.esm:0CD656` - `OutfitListSoldierImperialOfficerTullius` (LVLI)
  * `Skyrim.esm:0D768E` - `OutfitListSoldierImperialOfficerTulliusNoHelmet` (LVLI)

All three are the Tullius question the owner already settled: he wants Tullius in the Tribune
armour, so the replacer wins all three and New Legion's versions lose.

**Merge order:** Sons of Skyrim, then New Legion, then Tribune, then our own changes last.

## The duplicate to drop

Gypsymama's Tullius replacer carries its own copy of the Tribune armour - 5 ARMO and 11 ARMA - so
that it works standalone without the main mod. Merged as-is it would ship the set twice. Take the
Tribune ESL's 42 records, keep only the replacer's three override records, and repoint the outfit
lists at the Tribune ESL's armour.

## The hard part: translating references

Renumbering 893 records into ESL space is trivial. Fixing every reference TO them is not, and
getting it wrong corrupts a record silently rather than failing loudly.

`tools/derive-formid-slots.py` measures which `(record type, subrecord, offset)` slots hold values
that resolve to real records, across all four plugins; `docs/formid-slots-observed.txt` is its
output. It finds the real reference fields - `ARMA MODL` (the additional-races array), `ARMO MODL`
(the armature array), `COBJ CNTO/BNAM/CNAM`, `LVLI LVLO+4`, `OTFT INAM`, the WEAP sound and
keyword fields, `QUST` alias references, `REFR NAME` - but it also produces **false positives**,
because a string subrecord's bytes can look like a FormID: `ARMO MOD2 off=28`, `COBJ EDID off=28`
and `CONT OBND` are filenames and bounds, not references.

**So the measurement informs the schema; it does not replace it.** The merger gets an explicit,
hand-written table of FormID fields per record type, and the measurement is used to check that the
table has not missed a field that is demonstrably a reference.

**Verification, before the plugin is ever loaded:** re-read the merged output and, for every record,
compare it field by field against its source record with the FormID mapping applied in reverse.
Any byte that differs for a reason other than the renumbering is a bug. That check is cheap and it
is the difference between a merge that works and one that looks like it works.

## What this costs, stated plainly

**It breaks saves.** Sons of Skyrim is enabled in Njordlinger now. Merging renumbers all 667 of its
records, so an existing save loses everything that came from it.

**It forks three mods.** An update from NordwarUA or Gypsymama means re-running the merge, not
dropping in their file. The merger therefore reads the source plugins at build time, the same way
every other build script here does, so re-merging is one command rather than an afternoon.

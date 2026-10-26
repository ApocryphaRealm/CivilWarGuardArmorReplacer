# Civil War Guard Armor Replacer 2.0.0 - moving who-wears-what to SPID

Written 2026-10-26 for someone who was not in the session. Mod repo: `6. current wip mods\CivilWarGuardArmorReplacer`
(version-registry key `ApocryphaCivilWarGuardArmorReplacer`). Tools: `tools\spid-convert.py` (builds the plugin and the
ini), `tools\verify-spid.py` (offline proof against a Mod Organizer 2 load order).

## The request

The owner, 2026-10-26 00:12: *"I want the Civil War guard armor replacer to use SPID instead of an ESL or ESP."*

Background: 1.0.x is one hand-merged light plugin (`Civil War Guard Armor Replacer.esp`, ESPFE, 1312 records) built
from Sons of Skyrim, New Legion, Guards Armor Replacer and Imperial Tribune Armor. It dressed the guards by editing
264 vanilla NPC records and 45 vanilla outfits directly. The trigger for this work was naked Vigilants of Stendarr
(the cause turned out to be another mod - see the past-mistakes library, 2026-10-25 - but the lesson stands: a plugin
that edits shared NPC and outfit records has a large blast radius).

## What SPID can and cannot do

Spell Perk Item Distributor (SPID, Nexus 36869; Njordlinger has 7.2.1) reads `*_DISTR.ini` files and, at runtime,
gives NPCs **existing** forms - an outfit, items, spells, keywords - filtered by NPC, faction, keyword, race, the
outfit the plugins gave the NPC, level and more. It works on existing saves (SPID 7 re-dresses loaded actors).

It **cannot create a record**. Every armour piece in this mod (150 new ARMO, 295 ARMA, 29 weapons and the outfits and
levelled lists that group them) exists only because a plugin defines it. Vanilla has nowhere near enough armour
records to carry 150 distinct pieces, and turning the mod into loose meshes over vanilla paths would collapse the per-hold,
light/heavy/officer variety into one look per vanilla item - not "the guards looking as now". Using the source mods'
own plugins instead would bring back exactly the NPC/outfit edits we are removing, and lose our own edits (dragon-motif
sets removed, Tullius in the Tribune set, officer set, Windhelm patrol).

**So one plugin is unavoidable, and it is reduced to item records only.** It keeps its file name and every FormID, so
armour already in a save stays valid; it stays light (ESPFE, `.esp` with the light flag).

## Inventory of the 1.0.x plugin and where each group goes

| Records | Count | What they are | 2.0.0 |
|---|---|---|---|
| ARMO new / ARMA new | 150 / 295 | the armour itself | **kept** (plugin) |
| WEAP new, STAT new, AMMO, PROJ | 29, 30, 2, 2 | Sons of Skyrim / New Legion weapons; the STATs are the weapons' first-person models (WEAP WNAM), not displays | **kept** |
| COBJ new | 174 | crafting / tempering recipes for the new pieces | **kept** |
| ARMO / ARMA / WEAP / COBJ overrides | 35 / 4 / 1 / 6 | vanilla Imperial, Penitus and Stormcloak pieces whose mesh, name or tempering recipe the mod replaces | **kept** - an item record, not a distribution |
| OTFT new, LVLI new | 24, 133 | the mod's outfits and the levelled lists inside them | **kept** |
| OTFT overrides | 45 | vanilla outfits (GuardWhiterunOutfit...) rewritten to hold the mod's armour | **replaced** by new copies `CWGAR_<vanilla name>` with the same contents, handed out by SPID section A |
| LVLI overrides | 28 | vanilla levelled lists (outfit lists, soldier gear, player uniforms, bandit list) | **dropped**; where a distributed outfit still reaches one, a `CWGAR_` copy carries 1.0.x's contents (13 vanilla outfits that 1.0.x left alone but whose lists it rewrote get copies too) |
| NPC_ overrides | 264 | guards' outfit, plus Sons of Skyrim's inventory, class, race-field, stat and name edits | **dropped**; the outfit part moves to SPID (sections B and A). The non-outfit edits are not carried (see "What changes") |
| LVLN / CONT / QUST overrides | 2 / 10 / 2 | which guard variants spawn; blacksmith stock; Civil War and DB quest edits | **dropped** |
| CELL (4), REFR (65) | | Sons of Skyrim's armour displays in Dragonsreach, Winterhold Longhouse, Palace of the Kings (incl. 14 deleted vanilla clutter refs) and New Legion's rusted armour in Helgen Keep | **dropped** - not guards, cannot go through SPID |
| DIAL (2) / INFO (5) | | guard dialogue edits | **dropped** - cannot go through SPID |

Result: 956 records (885 kept + 71 `CWGAR_` copies), next light ID 0xBEF of 0xFFF.

### Placed references and dialogue - why dropped, not split out

SPID cannot place objects or edit dialogue. The options were to drop them or keep them in a second, optional plugin.
The owner asked for no plugin; a second plugin for decoration that is not part of "the guards look like X" would be
the opposite of that, and the displays are what pulled cells into the plugin in the first place (and what broke 1.0.0's
group tree). Dropping them is the simplest option that keeps the guards looking as now. Effect: the three palaces show
their vanilla clutter again, Helgen Keep loses five rusted Legion pieces, and five guard lines revert to vanilla.

## The SPID rules (`Civil War Guard Armor Replacer_DISTR.ini`)

Every form is written `0xID~Plugin` - no EditorIDs, so nothing depends on po3's Tweaks. Each line has a comment with
the EditorIDs. SPID gives an NPC the **first** outfit line it matches (its `for_first_form`), so the order matters:

* **Section B - named NPCs (32 lines, 259 NPCs).** The NPCs whose outfit 1.0.x set on the NPC record itself (the
  light / heavy / archer / officer variants and unique NPCs). Filter: the NPC, paired with the outfit it starts in
  where that outfit is its own (`0xNPC~Skyrim.esm+0xOUTFIT~Skyrim.esm`). SPID also matches an NPC filter against the
  NPC's template and, for a levelled actor, the list entry it was built from; so an NPC is named only when every NPC
  built from it should wear the same outfit. 26 template NPCs fail that test (e.g. EncGuardSons*, the Whiterun guard
  templates) and fall back to section A.
* **Section A - by vanilla outfit (58 lines).** `Outfit = CWGAR_X | NONE | X`: whoever the plugins dress in vanilla
  outfit X gets the mod's version of X. This is exactly the set 1.0.x's outfit override reached, no more.

### Scope - why the outfit, not a faction

The brief suggested faction scoping (per-hold guard factions). The first draft did that and the offline check showed
it only ever **removes** guards: Beyond Skyrim's Cyrodiil Imperial patrols, Winterhold Restored's guards and similar
NPCs from other mods wear the vanilla guard outfits but not the vanilla factions, and lost their look. The outfit filter
is narrower than any faction: SPID compares it with the outfit the plugins set (its "initial outfit"), so a line for
GuardWhiterunOutfit can only reach an NPC whose plugins dress it in GuardWhiterunOutfit. A Vigilant of Stendarr wears
VigilantOfStendarrOutfit and cannot match any line; nor can a bandit or a citizen.

## Verification (offline, Njordlinger Test, 1835 active plugins)

`tools\verify-spid.py --old <1.0.1 plugin> --new <2.0.0 plugin> --ini <ini> --instance D:\Modlists\Njordlinger --profile "Njordlinger Test"`:

* **forms**: 477 references on 90 lines, **0 unresolved** - every `0xID~Plugin` names an active plugin that defines a
  record of the right type (OTFT for the distributed form; OTFT / NPC_ for filters).
* **NPCs**: all 13,331 NPC records in the load order simulated - 1.0.x's outfit (winning records with 1.0.1 in place,
  'Use Inventory' templates followed) against 2.0.0 (winning records without 1.0.x's NPC/outfit edits, then the SPID
  lines applied first-match, with SPID's template ID rules). Outfits compared as the set of armour pieces they can give.
* **815 NPCs** get a CWGAR outfit. **0 GAINED** (nobody 1.0.x left alone gets this mod's armour), **0 LOST** (nobody
  1.0.x dressed is left in vanilla armour), **40 variant** (this mod's armour both times, another variant of it:
  levelled template NPCs whose possible outfits differ slightly, and Winterhold Restored's 7 guards, who now get the
  Winterhold set instead of the Imperial one, because 1.0.x reached them only through a two-level template chain).
* **Vigilants of Stendarr**: 78 by name or faction; **0 changed** by SPID.
* `esp-audit`: pass (every count matches, every own reference resolves, group tree correct).

Limits of the offline check: a levelled actor's template is chosen at spawn, so for those the check compares every
entry the list can pick; SkyPatcher or another distributor that rewrites outfits at runtime is not simulated (the only
other SPID outfit lines in Njordlinger are Companions and SD's Heavy Nordic, neither on guards).

## What changes for a player

* **Requirement added: Spell Perk Item Distributor 7.2 or later.** Without it the plugin still loads, the vanilla
  Imperial/Penitus/Stormcloak pieces still show the replaced art, but nobody is re-dressed.
* Guards and soldiers wear what they wore under 1.0.x (40 NPCs in another variant of the same set).
* Gone: armour displays in three palaces and Helgen Keep (vanilla clutter returns), blacksmiths stocking the armour
  (it can still be crafted), the Sons of Skyrim NPC edits that were not the outfit (inventory weapons - guards carry
  vanilla weapons again; stats, classes, names), the Civil War quest and Dark Brotherhood quest edits, the player's
  Stormcloak/Imperial uniform and bear-armour reward lists, five guard dialogue lines.
* Existing saves: armour in the player's inventory keeps working (same FormIDs); SPID re-dresses guards on load.

## Version

**2.0.0 (major).** Removing records that saves and other plugins can reference (placed refs, NPC and quest edits) and
adding a required framework is a breaking change under the version rules (rule 6: when unsure, major). 1.0.1 was open
and unposted; `version-gate bump -Kind major` withdrew it and issued 2.0.0 from the last posted 1.0.0.

# What ships when

Two versions, in this order, because the second one only makes sense once the first exists.

## 1.0.0 - the assembly

Sons of Skyrim, New Legion, Guards Armor Replacer's Winterhold and Windhelm Scale sets, and the
Imperial Tribune armour with Tullius wearing it, as one install behind **one merged light plugin**.
`plugin-merge-analysis.md` records what that merge contains.

**BodySlide is part of 1.0.0, not an afterthought.** The owner, 2026-09-16: *"I think we should make
sure that we build in the body slide, body shape sliders and everything"*. So the package ships the
slider sets and shape data for every armour in it, and the build refuses if any armour in the mod
has no slider set - the same shape of check the other build scripts use, because a body refit that
silently covers three armours out of four is worse than none at all.

What exists on Nexus today, and where it runs out:

| Armour | CBBE / 3BA | HIMBO |
|---|---|---|
| Sons of Skyrim | 88218 | 88218 |
| Guards Armor Replacer | 43473 | 53294 |
| New Legion | **none found** | 53308 |
| Imperial Tribune | **none; the mod ships no BodySlide at all** | **none** |

The two gaps are ours to close in Outfit Studio. That is ordinary refit work, not research, but it
is work, and it is the long pole in 1.0.0 rather than the merge.

## The version after - one consistent armoury

The owner, same day: *"in a version that comes after that merge, we should renumber or recategorize
all the armor so that it's all consistent and more uniform"*.

Four mods by three authors, assembled, means four different conventions sitting side by side:
editor IDs (`0_Windhelm_Armor_Heavy`, `DIS_Officer_CuirassA`, and the Tribune's own), display names,
keyword sets, armour ratings and weights pitched against different baselines, and crafting recipes
that appear under different stations and perks. A player sees that as an armoury that does not quite
hang together.

So the follow-up pass normalises, across every armour in the merged plugin:

* **editor IDs**, to one scheme, so the plugin is navigable in xEdit;
* **display names**, so the same rank reads the same way on both sides of the war;
* **keywords**, so material and armour-type keywords are complete and consistent - which is what
  smithing perks, tempering and other mods' patches actually key off;
* **FormID order**, grouped by faction and slot rather than by which mod a record came from;
* **stats and recipes**, pitched against one baseline instead of three.

Deliberately a separate version. Merging is mechanical and verifiable - the output can be compared
against its sources byte for byte. Renumbering and rebalancing is a judgement call about every
record, and it needs to be reviewable on its own, against a 1.0.0 that is already known to work.

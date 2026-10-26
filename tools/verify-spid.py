#!/usr/bin/env python3
r"""Prove offline that the 2.0.0 plugin + SPID ini dress every NPC exactly as 1.0.x did, and nobody else.

WHAT IT DOES, against a real Mod Organizer 2 profile's load order
    1. Resolves every 0xID~Plugin in the _DISTR.ini: the plugin must be active in the profile and must DEFINE a
       record with that ID, of the type the line needs (Outfit = OTFT; filters = OTFT / FACT / NPC_).
    2. For every NPC in the load order it works out the outfit 1.0.x left it in (the winning NPC record, with the
       1.0.x plugin in its place) and the outfit it wears under 2.0.0 (the winning record WITHOUT 1.0.x's NPC and
       outfit overrides, then the SPID lines applied the way SPID 7 applies them: the FIRST matching line wins,
       section B by NPC (+ starting outfit), section A by the outfit the plugins set; templates followed for 'Use Inventory' and 'Use Factions').
    3. Compares the two for every NPC, item by item: an outfit is reduced to the set of armour pieces its
       levelled lists can give, read from the 1.0.x plugin for 1.0.x and from the 2.0.0 plugin for 2.0.0.
    It prints every difference, every NPC SPID changes, and a separate line for the Vigilants of Stendarr.
    Exit 1 on an unresolved form, on any NPC 2.0.0 dresses in this mod's armour that 1.0.x did not, on any
    change to an outfit made only of vanilla pieces, or on any Vigilant of Stendarr whose outfit SPID changes.
    'variant' and 'LOST' differences are listed for review.

Usage:
    py -3 tools/verify-spid.py --old "<1.0.x plugin>" --new "plugin/Civil War Guard Armor Replacer.esp"
                               --ini "spid/Civil War Guard Armor Replacer_DISTR.ini"
                               --instance "D:\Modlists\Njordlinger" --profile "Njordlinger Test"
"""
import argparse
import collections
import os
import re
import struct
import sys
import zlib

PLUGIN = "Civil War Guard Armor Replacer.esp"
BASE = ("skyrim.esm", "update.esm", "dawnguard.esm", "hearthfires.esm", "dragonborn.esm")
WANT = {"NPC_", "OTFT", "FACT", "LVLN", "LVLI", "ARMO"}


def subs(body):
    out, i, big = [], 0, None
    while i + 6 <= len(body):
        s = body[i:i + 4].decode("latin-1")
        n = struct.unpack_from("<H", body, i + 4)[0]
        if s == "XXXX":
            big = struct.unpack_from("<I", body, i + 6)[0]
            i += 6 + n
            continue
        if big is not None:
            n, big = big, None
        out.append((s, body[i + 6:i + 6 + n]))
        i += 6 + n
    return out


def scan(path):
    data = open(path, "rb").read()
    size = struct.unpack_from("<I", data, 4)[0]
    masters = [d.rstrip(b"\0").decode("latin-1") for s, d in subs(data[24:24 + size]) if s == "MAST"]
    recs, defined = [], {}

    def walk(off, end):
        while off < end:
            sig = data[off:off + 4].decode("latin-1")
            sz = struct.unpack_from("<I", data, off + 4)[0]
            if sig == "GRUP":
                walk(off + 24, off + sz)
                off += sz
                continue
            fl, fid = struct.unpack_from("<II", data, off + 8)
            if (fid >> 24) >= len(masters):
                defined[fid & 0xFFFFFF] = sig
            if sig in WANT and not fl & 0x20:
                body = data[off + 24:off + 24 + sz]
                if fl & 0x40000:
                    body = zlib.decompress(body[4:])
                recs.append((sig, fid, body))
            off += 24 + sz

    walk(24 + size, len(data))
    return masters, recs, defined


def profile(instance, prof):
    mods = [l.rstrip("\n")[1:] for l in open(os.path.join(instance, "profiles", prof, "modlist.txt"), encoding="utf-8")
            if l.startswith("+")]
    paths = {}
    data = os.path.join(instance, "Stock Game", "Data")
    for f in os.listdir(data):
        if f.lower().endswith((".esp", ".esm", ".esl")):
            paths[f.lower()] = os.path.join(data, f)
    for m in reversed(mods):
        d = os.path.join(instance, "mods", m)
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.lower().endswith((".esp", ".esm", ".esl")):
                    paths[f.lower()] = os.path.join(d, f)
    active = {l.strip()[1:].lower() for l in open(os.path.join(instance, "profiles", prof, "plugins.txt"), encoding="utf-8")
              if l.strip().startswith("*")}
    order = [l.strip() for l in open(os.path.join(instance, "profiles", prof, "loadorder.txt"), encoding="utf-8")
             if l.strip() and not l.startswith("#") and (l.strip().lower() in active or l.strip().lower() in BASE)]
    return order, paths


class World:
    """Winning records of one load order."""

    def __init__(self, order, scans, cw_override=None):
        self.rec, self.defined, self._cache, self._items = {}, {}, {}, {}
        for p in order:
            if p.lower() == PLUGIN.lower() and cw_override is not None:
                masters, recs, defined = cw_override
            elif p.lower() in scans:
                masters, recs, defined = scans[p.lower()]
            else:
                continue
            self.defined[p.lower()] = defined
            for sig, fid, body in recs:
                i = fid >> 24
                owner = (masters[i] if i < len(masters) else p).lower()
                self.rec[(owner, fid & 0xFFFFFF)] = (sig, masters, p, body)

    def ref(self, key, raw):
        sig, masters, p, body = self.rec[key]
        fid = struct.unpack_from("<I", raw)[0]
        i = fid >> 24
        return ((masters[i] if i < len(masters) else p).lower(), fid & 0xFFFFFF)

    def _subs(self, key):
        c = self._cache.get(key)
        if c is None:
            c = self._cache[key] = subs(self.rec[key][3])
        return c

    def get(self, key, name):
        if key not in self.rec:
            return None
        for s, d in self._subs(key):
            if s == name:
                return d
        return None

    def all(self, key, name):
        return [d for s, d in self._subs(key) if s == name] if key in self.rec else []

    def edid(self, key):
        v = self.get(key, "EDID")
        return v.rstrip(b"\0").decode("latin-1") if v else "?"

    def template_chain(self, key, flag, depth=0):
        """Follow TPLT while the NPC takes `flag` (0x04 factions, 0x100 inventory) from its template; flag 0 follows
        every template link (SPID matches an NPC filter against the whole template chain - conservative)."""
        if depth > 8 or key not in self.rec:
            return [key]
        sig = self.rec[key][0]
        if sig == "LVLN":
            return [key]
        acbs, tplt = self.get(key, "ACBS"), self.get(key, "TPLT")
        if tplt and (flag == 0 or (acbs and struct.unpack_from("<H", acbs, 18)[0] & flag)):
            return [key] + self.template_chain(self.ref(key, tplt), flag, depth + 1)
        return [key]

    def outfit(self, key):
        last = self.template_chain(key, 0x100)[-1]
        if last not in self.rec:
            return None
        if self.rec[last][0] == "LVLN":
            return ("LVLN", last)
        d = self.get(last, "DOFT")
        return self.ref(last, d) if d else None

    def factions(self, key, depth=0):
        last = self.template_chain(key, 0x04)[-1]
        if last not in self.rec or depth > 8:
            return set()
        if self.rec[last][0] == "LVLN":
            out = None
            for d in self.all(last, "LVLO"):
                f = self.factions(self.ref(last, d[4:8]), depth + 1)
                out = f if out is None else out & f
            return out or set()
        return {self.ref(last, d[:4]) for d in self.all(last, "SNAM")}

    def items(self, key, depth=0):
        """Every armour piece an outfit / levelled list can give."""
        if key in self._items:
            return self._items[key]
        if key is None or key not in self.rec or depth > 12:
            return frozenset()
        r = self._items_uncached(key, depth)
        self._items[key] = r
        return r

    def _items_uncached(self, key, depth):
        sig = self.rec[key][0]
        if sig == "ARMO":
            return frozenset([key])
        out = set()
        if sig == "OTFT":
            d = self.get(key, "INAM") or b""
            for i in range(0, len(d), 4):
                out |= self.items(self.ref(key, d[i:i + 4]), depth + 1)
        elif sig == "LVLI":
            for d in self.all(key, "LVLO"):
                out |= self.items(self.ref(key, d[4:8]), depth + 1)
        return frozenset(out)


FORM = re.compile(r"^(-?)0x([0-9A-Fa-f]+)~(.+)$")


def parse_ini(path):
    rules = []
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.split(";", 1)[0].strip()
        if not line:
            continue
        key, val = [x.strip() for x in line.split("=", 1)]
        fields = val.split("|")
        rules.append((n, key, fields))
    return rules


def form_key(tok):
    m = FORM.match(tok.strip())
    if not m:
        return None, None
    return m.group(1) == "-", (m.group(3).lower(), int(m.group(2), 16))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--ini", required=True)
    ap.add_argument("--instance", required=True)
    ap.add_argument("--profile", required=True)
    a = ap.parse_args()

    order, paths = profile(a.instance, a.profile)
    if PLUGIN.lower() not in [p.lower() for p in order]:
        print(f"FAIL: {PLUGIN} is not active in {a.profile}")
        return 1
    scans = {}
    for p in order:
        fp = paths.get(p.lower())
        if fp and p.lower() != PLUGIN.lower():
            scans[p.lower()] = scan(fp)
    old_w = World(order, scans, cw_override=scan(a.old))
    new_scan = scan(a.new)
    new_w = World(order, scans, cw_override=new_scan)
    # 2.0.0's world before SPID: the new plugin defines no NPC or vanilla outfit override, which new_w already is.

    # ---- 1. every form in the ini resolves
    bad = 0
    rules = parse_ini(a.ini)
    active = {p.lower() for p in order}
    parsed = []
    for n, key, fields in rules:
        if key != "Outfit":
            print(f"FAIL line {n}: unexpected key {key}")
            bad += 1
            continue
        _, outfit = form_key(fields[0])
        toks = []
        for alt in (fields[2].split(",") if len(fields) > 2 and fields[2] != "NONE" else []):
            group = []
            for t in alt.split("+"):
                neg, k = form_key(t)
                group.append((neg, k))
            toks.append(group)
        for neg, k in [(False, outfit)] + [x for g in toks for x in g]:
            if k is None:
                print(f"FAIL line {n}: a form is not written as 0xID~Plugin")
                bad += 1
                continue
            if k[0] not in active:
                print(f"FAIL line {n}: {k[0]} is not active in the profile")
                bad += 1
                continue
            sig = new_w.defined.get(k[0], {}).get(k[1])
            if sig is None:
                print(f"FAIL line {n}: {k[0]} defines no record 0x{k[1]:X}")
                bad += 1
        if new_w.rec.get(outfit, ("",))[0] != "OTFT":
            print(f"FAIL line {n}: the distributed form 0x{outfit[1]:X} is not an outfit")
            bad += 1
        parsed.append((n, outfit, toks))
    print(f"forms: {sum(1 + sum(len(g) for g in t) for _, _, t in parsed)} references on {len(parsed)} lines, {bad} unresolved")

    # ---- 2/3. simulate
    def matches(npc, toks, initial, facs):
        pos = [g for g in toks if not all(neg for neg, _ in g)]
        negs = [k for g in toks for neg, k in g if neg]

        def has(k):
            sig = new_w.rec.get(k, ("?",))[0]
            if sig == "OTFT":
                return initial == k
            if sig == "FACT":
                return k in facs
            if sig in ("NPC_", "LVLN"):
                return k in spid_ids(npc)
            return False
        if any(has(k) for k in negs):
            return False
        return not pos or any(all(has(k) for neg, k in g if not neg) for g in pos)

    def lvln_entries(key, depth=0):
        if depth > 8 or new_w.rec.get(key, ("",))[0] != "LVLN":
            return {key}
        out = set()
        for d in new_w.all(key, "LVLO"):
            out |= lvln_entries(new_w.ref(key, d[4:8]), depth + 1)
        return out

    _ids = {}

    def spid_ids(npc):
        if npc not in _ids:
            _ids[npc] = _spid_ids(npc)
        return _ids[npc]

    def _spid_ids(npc):
        """SPID 7 matches an NPC filter against the NPC, its direct template (baseTemplateForm) and, for a
        levelled actor, the template it was built from - modelled here as ANY entry of the levelled list."""
        ids = {npc}
        t = new_w.get(npc, "TPLT")
        if t:
            tk = new_w.ref(npc, t)
            ids.add(tk)
            ids |= lvln_entries(tk)
        return ids

    cw_l = PLUGIN.lower()
    # an armour piece that shows this mod's art: defined by the plugin, or a vanilla piece the plugin overrides
    mod_old = {k for k, v in old_w.rec.items() if v[0] == "ARMO" and v[2].lower() == cw_l}
    mod_new = {k for k, v in new_w.rec.items() if v[0] == "ARMO" and v[2].lower() == cw_l}
    npcs = [k for k, v in new_w.rec.items() if v[0] == "NPC_"]
    diffs, changed, vig = [], collections.Counter(), []
    for npc in npcs:
        old_o = old_w.outfit(npc)
        initial = new_w.outfit(npc)
        facs = new_w.factions(npc)
        result = initial
        for n, outfit, toks in parsed:      # SPID 7: the first outfit line an NPC matches is the one it gets
            if matches(npc, toks, initial, facs):
                result = outfit
                break
        if old_o and old_o[0] == "LVLN" and result and result[0] == "LVLN":
            # a levelled template: the outfit is picked when the actor spawns. Check every entry it can pick -
            # each entry, run through the same SPID lines, must give what 1.0.x gave that entry.
            entries = lvln_entries(result[1])
            olds = {old_w.items(old_w.outfit(e)) if old_w.outfit(e) and old_w.outfit(e)[0] != "LVLN" else frozenset() for e in entries}
            news = set()
            for e in entries:
                ei = new_w.outfit(e)
                er = ei
                for n, outfit, toks in parsed:
                    if matches(npc, toks, ei, facs):
                        er = outfit
                        break
                news.add(new_w.items(er) if er and er[0] != "LVLN" else frozenset())
            old_items, new_items = frozenset().union(*olds), frozenset().union(*news)
        else:
            old_items = old_w.items(old_o) if old_o and old_o[0] != "LVLN" else frozenset()
            new_items = new_w.items(result) if result and result[0] != "LVLN" else frozenset()
        if result != initial:
            changed[new_w.edid(result)] += 1
        if old_items != new_items:
            om, nm_ = bool(old_items & mod_old), bool(new_items & mod_new)
            kind = "variant" if om and nm_ else "LOST" if om else "GAINED" if nm_ else "vanilla-only"
            diffs.append((kind, npc, old_o, initial, result))
        name = new_w.edid(npc).lower()
        if "vigilant" in name or any("vigilant" in new_w.edid(f).lower() for f in facs):
            vig.append((npc, initial, result))
    print(f"NPCs: {len(npcs)} in the load order; SPID gives a CWGAR outfit to {sum(changed.values())}")
    for e, c in changed.most_common():
        print(f"   {c:4d}  {e}")
    kinds = collections.Counter(d[0] for d in diffs)
    print(f"differences from 1.0.x (by armour pieces): {len(diffs)} {dict(kinds)}")
    print("   variant = this mod's armour both times, another variant of it; LOST = 1.0.x gave this mod's armour,")
    print("   2.0.0 does not; GAINED = 2.0.0 gives this mod's armour to an NPC 1.0.x did not dress (a failure)")
    for kind, npc, old_o, ini, res in sorted(diffs, key=lambda d: d[0]):
        print(f"   {kind:8s} {npc[0]}:{npc[1]:06X} {new_w.edid(npc)}: 1.0.x {old_w.edid(old_o) if old_o and old_o[0] != 'LVLN' else '-'} "
              f"| 2.0.0 before SPID {new_w.edid(ini) if ini and ini[0] != 'LVLN' else '-'} -> after SPID "
              f"{new_w.edid(res) if res and res[0] != 'LVLN' else '-'}")
    vchanged = [v for v in vig if v[1] != v[2]]
    print(f"Vigilants of Stendarr (by name or faction): {len(vig)}; changed by SPID: {len(vchanged)}")
    for npc, ini, res in vchanged:
        print(f"   VIGILANT CHANGED {new_w.edid(npc)}: {new_w.edid(ini)} -> {new_w.edid(res)}")
    return 1 if bad or kinds.get('GAINED') or kinds.get('vanilla-only') or vchanged else 0


if __name__ == "__main__":
    sys.exit(main())

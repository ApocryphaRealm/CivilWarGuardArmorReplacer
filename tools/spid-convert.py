#!/usr/bin/env python3
r"""Turn the 1.0.x merged plugin into an item-only plugin plus a SPID _DISTR.ini (2.0.0).

WHY
    The owner, 2026-10-26: "I want the Civil War guard armor replacer to use SPID instead of an ESL or ESP."
    Spell Perk Item Distributor (SPID) can hand an EXISTING outfit to NPCs at runtime, filtered by the outfit
    they already wear, by faction or by NPC - but it cannot create a record. The armour itself (150 new
    ARMO, 295 ARMA and the outfits and levelled lists that group them) only exists because a plugin defines
    it, so a plugin stays - reduced to item records. Everything in 1.0.x that decided WHO wears WHAT, or
    touched the world, quests or dialogue, is removed from the plugin; who-wears-what moves to SPID.
    See docs/spid-design.md (the copy of 4. plans\cwgar-spid\DESIGN.md) for the full reasoning.

WHAT THE PLUGIN KEEPS (FormIDs unchanged, so items already in a save stay valid)
    * every NEW record of type ARMO ARMA OTFT LVLI WEAP AMMO PROJ COBJ STAT (the 30 STATs are the weapons'
      first-person models, WEAP WNAM - not display pieces);
    * overrides of vanilla ARMO / ARMA / WEAP / COBJ (the vanilla Imperial, Penitus and Stormcloak pieces
      whose look, name or tempering recipe the mod replaces - an item record, not a distribution);
    * NEW copies ("CWGAR_<vanilla EditorID>") of every vanilla outfit or levelled list 1.0.x overrode and that
      a distributed outfit still reaches - the copy carries 1.0.x's contents, so the guard wears the same
      thing, but the vanilla record is no longer edited and reaches nobody new.

WHAT IT DROPS
    NPC_ (264), vanilla OTFT (45) / LVLI (28) / LVLN (2) / CONT (10) / QUST (2) overrides, CELL (4),
    REFR (65 - Sons of Skyrim's armour displays, the 14 vanilla clutter refs it deleted, New Legion's Helgen
    pieces), DIAL (2) / INFO (5).

THE SPID RULES IT WRITES
    A  one line per vanilla outfit 1.0.x overrode (or left alone but whose levelled lists it overrode):
           Outfit = CWGAR copy | NONE | <vanilla outfit>
       - "whoever the plugins dress in GuardWhiterunOutfit" - exactly the set 1.0.x's override reached. SPID gives
       the FIRST matching line, so section B is written first and A needs no exclusions. No faction is added: the outfit already is the narrowest scope, and a faction
       only drops guards other mods add (Beyond Skyrim's Cyrodiil patrols lost their look in the first draft).
    B  one line per outfit 1.0.x gave to particular NPCs (the NPC_ overrides): Outfit = X | NONE | NPC+start,...
       (each NPC paired with the outfit it starts in where that is its own), written before section A.
    Every form is written as 0xID~Plugin (never an EditorID), so nothing depends on EditorIDs being loaded.

Usage (the 1.0.x source plugin is in git: git show b3a019e:"plugin/Civil War Guard Armor Replacer.esp" > src.esp):
    py -3 tools/spid-convert.py --src "<1.0.x plugin>" --out "plugin/Civil War Guard Armor Replacer.esp"
                                --ini "spid/Civil War Guard Armor Replacer_DISTR.ini" [--report <json>]
    Masters are read from CWGAR_SKYRIM_DATA (Skyrim.esm, Update.esm) and CWGAR_DLC_DATA (the three DLC
    masters); defaults are the Njordlinger instance's Stock Game\Data and its "Base Game DLC Content" mod.
"""
import argparse
import json
import os
import struct
import sys
import zlib

PLUGIN = "Civil War Guard Armor Replacer.esp"
SKYRIM_DATA = os.environ.get("CWGAR_SKYRIM_DATA", r"D:\Modlists\Njordlinger\Stock Game\Data")
DLC_DATA = os.environ.get("CWGAR_DLC_DATA", r"D:\Modlists\Njordlinger\mods\Base Game DLC Content")

KEEP_NEW = {"ARMO", "ARMA", "OTFT", "LVLI", "WEAP", "AMMO", "PROJ", "COBJ", "STAT"}
KEEP_OVERRIDE = {"ARMO", "ARMA", "WEAP", "COBJ"}
LIGHT_FLAG = 0x200
COMPRESSED = 0x40000


TOP_ORDER = ("GMST KYWD LCRT AACT TXST GLOB CLAS FACT HDPT HAIR EYES RACE SOUN ASPC MGEF SCPT LTEX ENCH SPEL SCRL "
             "ACTI TACT ARMO BOOK CONT DOOR INGR LIGH MISC APPA STAT SCOL MSTT PWAT GRAS TREE CLDC FLOR FURN WEAP "
             "AMMO NPC_ LVLN KEYM ALCH IDLM COBJ PROJ HAZD SLGM LVLI WTHR CLMT SPGD RFCT REGN NAVI CELL WRLD DIAL "
             "QUST IDLE PACK CSTY LSCR LVSP ANIO WATR EFSH EXPL DEBR IMGS IMAD FLST PERK BPTD ADDN AVIF CAMS CPTH "
             "VTYP MATT IPCT IPDS ARMA ECZN LCTN MESG RGDL DOBJ LGTM MUSC FSTP FSTS SMBN SMQN SMEN DLBR MUST DLVW "
             "WOOP SHOU EQUP RELA SCEN ASTP OTFT ARTO MATO MOVT SNDR DUAL SNCT SOPM COLL CLFM REVB").split()


def fail(msg):
    print("REFUSED: " + msg, file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------- reading

class Rec:
    def __init__(self, sig, flags, fid, tail, raw, body):
        self.sig, self.flags, self.fid, self.tail, self.raw, self.body = sig, flags, fid, tail, raw, body

    def subs(self):
        out, i, big = [], 0, None
        b = self.body
        while i + 6 <= len(b):
            s = b[i:i + 4].decode("latin-1")
            n = struct.unpack_from("<H", b, i + 4)[0]
            if s == "XXXX":
                big = struct.unpack_from("<I", b, i + 6)[0]
                i += 6 + n
                continue
            if big is not None:
                n, big = big, None
            out.append((s, b[i + 6:i + 6 + n]))
            i += 6 + n
        return out

    def get(self, name):
        for s, d in self.subs():
            if s == name:
                return d
        return None

    @property
    def edid(self):
        v = self.get("EDID")
        return v.rstrip(b"\0").decode("latin-1") if v else ""


def read_plugin(path):
    data = open(path, "rb").read()
    recs = []

    def walk(off, end):
        while off < end:
            sig = data[off:off + 4].decode("latin-1")
            size = struct.unpack_from("<I", data, off + 4)[0]
            if sig == "GRUP":
                walk(off + 24, off + size)
                off += size
                continue
            flags, fid = struct.unpack_from("<II", data, off + 8)
            tail = data[off + 16:off + 24]
            raw = data[off + 24:off + 24 + size]
            body = zlib.decompress(raw[4:]) if flags & COMPRESSED else raw
            recs.append(Rec(sig, flags, fid, tail, raw, body))
            off += 24 + size

    walk(0, len(data))
    if not recs or recs[0].sig != "TES4":
        fail(path + " does not start with a TES4 header")
    hdr = recs[0]
    masters = [d.rstrip(b"\0").decode("latin-1") for s, d in hdr.subs() if s == "MAST"]
    return hdr, masters, recs[1:]


def load_masters(names):
    """(master name lower, local id) -> Rec, for the records the conversion asks about."""
    want = {"NPC_", "OTFT", "LVLI", "FACT", "LVLN"}
    db = {}
    for name in names:
        folder = SKYRIM_DATA if name.lower() in ("skyrim.esm", "update.esm") else DLC_DATA
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            fail(f"master {name} not found at {path} (set CWGAR_SKYRIM_DATA / CWGAR_DLC_DATA)")
        hdr, ms, recs = read_plugin(path)
        for r in recs:
            if r.sig not in want:
                continue
            i = r.fid >> 24
            owner = ms[i] if i < len(ms) else name
            db[(owner.lower(), r.fid & 0xFFFFFF)] = (name, ms, r)
    return db


# ---------------------------------------------------------------- writing

def subrec(sig, data):
    if len(data) > 0xFFFF:
        return b"XXXX" + struct.pack("<HI", 4, len(data)) + sig.encode() + struct.pack("<H", 0) + data
    return sig.encode() + struct.pack("<H", len(data)) + data


def build_body(subs):
    return b"".join(subrec(s, d) for s, d in subs)


def record_bytes(sig, flags, fid, tail, body):
    flags &= ~COMPRESSED
    return sig.encode() + struct.pack("<III", len(body), flags, fid) + tail + body


def raw_record(r):
    return r.sig.encode() + struct.pack("<III", len(r.raw), r.flags, r.fid) + r.tail + r.raw


def group(label, payload):
    return b"GRUP" + struct.pack("<I", 24 + len(payload)) + label.encode() + struct.pack("<iI", 0, 0) + \
        struct.pack("<I", 0) + payload


# ---------------------------------------------------------------- conversion

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ini", required=True)
    ap.add_argument("--report")
    a = ap.parse_args()

    hdr, masters, recs = read_plugin(a.src)
    nm = len(masters)
    if not hdr.flags & LIGHT_FLAG:
        fail("source plugin is not light-flagged")
    mdb = load_masters(masters)

    def canon(fid):            # FormID in OUR plugin's space -> (owner lower, local id)
        i = fid >> 24
        return (masters[i].lower() if i < nm else PLUGIN.lower(), fid & 0xFFFFFF)

    def master_to_ours(mname, mmasters, fid):    # a master record's FormID -> our plugin's space
        i = fid >> 24
        owner = mmasters[i] if i < len(mmasters) else mname
        if owner not in masters:
            fail(f"{mname} references {owner}, which is not a master of the plugin")
        return (masters.index(owner) << 24) | (fid & 0xFFFFFF)

    def is_new(r):
        return (r.fid >> 24) >= nm

    by_fid = {r.fid: r for r in recs}
    ovr_lists = {r.fid: r for r in recs if not is_new(r) and r.sig in ("OTFT", "LVLI")}

    # --- next free light ID
    hedr = hdr.get("HEDR")
    hver, hcount, next_id = struct.unpack("<fiI", hedr)
    used = max(r.fid & 0xFFF for r in recs if is_new(r))
    next_id = max(next_id, used + 1, 0x800)

    copies = {}                # vanilla fid (our space) -> new fid
    out_records = {}           # fid -> (sig, flags, fid, tail, body) for rebuilt records
    queue = []

    def copy_of(fid):
        nonlocal next_id
        if fid in copies:
            return copies[fid]
        if next_id > 0xFFF:
            fail("ran out of light FormIDs (0x800-0xFFF)")
        new = (nm << 24) | next_id
        next_id += 1
        copies[fid] = new
        queue.append(fid)
        return new

    reach_cache = {}

    def vanilla_reaches_override(fid, seen=None):
        """A vanilla outfit / levelled list whose contents (at any depth) include a list 1.0.x overrode."""
        if fid in reach_cache:
            return reach_cache[fid]
        seen = seen or set()
        c = canon(fid)
        if c[0] == PLUGIN.lower() or c not in mdb or fid in seen:
            return False
        seen.add(fid)
        mname, mms, mr = mdb[c]
        hit = False
        for s_, d in mr.subs():
            refs = []
            if mr.sig == "OTFT" and s_ == "INAM":
                refs = struct.unpack(f"<{len(d) // 4}I", d)
            elif mr.sig == "LVLI" and s_ == "LVLO":
                refs = [struct.unpack_from("<I", d, 4)[0]]
            for x in refs:
                ours = master_to_ours(mname, mms, x)
                if ours in ovr_lists or vanilla_reaches_override(ours, seen):
                    hit = True
        reach_cache[fid] = hit
        return hit

    def needs_copy(fid):
        return fid in ovr_lists or ((fid >> 24) < nm and vanilla_reaches_override(fid))

    def list_refs_rewritten(sig, subs):
        """Point every outfit/levelled-list entry that names a list 1.0.x overrode - or a vanilla list that holds
        one, at any depth - at our copy of it, so the copy gives exactly what 1.0.x gave."""
        out = []
        for s_, d in subs:
            if sig == "OTFT" and s_ == "INAM":
                ids = list(struct.unpack(f"<{len(d) // 4}I", d))
                ids = [copy_of(x) if needs_copy(x) else x for x in ids]
                d = struct.pack(f"<{len(ids)}I", *ids)
            elif sig == "LVLI" and s_ == "LVLO":
                ref = struct.unpack_from("<I", d, 4)[0]
                if needs_copy(ref):
                    d = d[:4] + struct.pack("<I", copy_of(ref)) + d[8:]
            out.append((s_, d))
        return out

    # kept new OTFT / LVLI get their references rewritten; everything else kept is copied byte for byte
    kept, dropped = [], {}
    for r in recs:
        keep = (is_new(r) and r.sig in KEEP_NEW) or (not is_new(r) and r.sig in KEEP_OVERRIDE)
        if not keep:
            dropped[r.sig] = dropped.get(r.sig, 0) + 1
            continue
        kept.append(r)
        if is_new(r) and r.sig in ("OTFT", "LVLI"):
            out_records[r.fid] = (r.sig, r.flags, r.fid, r.tail, build_body(list_refs_rewritten(r.sig, r.subs())))

    # every vanilla outfit 1.0.x overrode gets a copy (rule A distributes it)
    for fid, r in ovr_lists.items():
        if r.sig == "OTFT":
            copy_of(fid)

    # rule-A outfits: every vanilla outfit 1.0.x overrode, plus every vanilla outfit that was left alone but holds a
    # levelled list 1.0.x overrode (its wearers saw 1.0.x's list contents, so they get a copy that still does)
    a_outfits = sorted(f for f, r in ovr_lists.items() if r.sig == "OTFT")
    lower_masters = [m.lower() for m in masters]
    for c, (mname, mms, mr) in sorted(mdb.items()):
        if mr.sig != "OTFT" or c[0] not in lower_masters:
            continue
        fid = (lower_masters.index(c[0]) << 24) | c[1]
        if fid not in ovr_lists and vanilla_reaches_override(fid):
            a_outfits.append(fid)
            copy_of(fid)
    a_set = set(a_outfits)

    # --- NPC outfits 1.0.x set (rule B). An NPC's outfit is read where the game reads it: an NPC that takes its
    # inventory from a template ('Use Inventory') wears the template's outfit, so 1.0.x's change to a template
    # reached every NPC built from it. Both views follow that chain; a levelled template ends it (decided at runtime).
    cw_npc = {canon(r.fid): r for r in recs if r.sig == "NPC_" and not is_new(r)}

    def view(c, use_cw):
        if use_cw and c in cw_npc:
            r = cw_npc[c]
            return r.get("ACBS"), r.get("TPLT"), r.get("DOFT"), None, None, True
        if c in mdb and mdb[c][2].sig == "NPC_":
            mname, mms, mr = mdb[c]
            return mr.get("ACBS"), mr.get("TPLT"), mr.get("DOFT"), mname, mms, False
        return None

    def effective_outfit(c, use_cw, depth=0):
        v = view(c, use_cw)
        if v is None or depth > 8:
            return None
        acbs, tplt, doft, mname, mms, ours = v
        conv = (lambda x: x) if ours else (lambda x: master_to_ours(mname, mms, x))
        if acbs and tplt and struct.unpack_from("<H", acbs, 18)[0] & 0x100:
            t = canon(conv(struct.unpack("<I", tplt)[0]))
            if t in mdb and mdb[t][2].sig == "LVLN":
                return None
            return effective_outfit(t, use_cw, depth + 1)
        return conv(struct.unpack("<I", doft)[0]) if doft else None

    npc_rules = {}             # outfit fid (our space, mapped to a copy where needed) -> [npc canon]
    npc_initial = {}           # npc canon -> the outfit the plugins give it without 1.0.x (SPID's outfit filter)
    for c, (mname, mms, mr) in mdb.items():
        if mr.sig != "NPC_":
            continue
        old = effective_outfit(c, True)
        new = effective_outfit(c, False)
        want = copy_of(old) if old in a_set else old
        base = copy_of(new) if new in a_set else new
        if want is None or want == base:
            continue
        npc_rules.setdefault(want, []).append(c)
        npc_initial[c] = new

    vanilla_copies = {}
    for outfit in list(npc_rules):
        if (outfit >> 24) < nm and outfit not in copies and vanilla_reaches_override(outfit, set()):
            vanilla_copies[outfit] = True
            npc_rules[copy_of(outfit)] = npc_rules.pop(outfit)

    # --- build the copies (breadth first; a copy may ask for more copies)
    while queue:
        fid = queue.pop(0)
        new = copies[fid]
        if fid in ovr_lists:
            src = ovr_lists[fid]
            subs, flags, tail, sig = src.subs(), src.flags, src.tail, src.sig
        else:                                   # a vanilla outfit rule B needs, copied from its master
            mname, mms, mr = mdb[canon(fid)]
            subs, flags, tail, sig = [], mr.flags, mr.tail, mr.sig
            for s, d in mr.subs():
                if mr.sig == "OTFT" and s == "INAM":
                    ids = [master_to_ours(mname, mms, x) for x in struct.unpack(f"<{len(d) // 4}I", d)]
                    d = struct.pack(f"<{len(ids)}I", *ids)
                elif mr.sig == "LVLI" and s == "LVLO":
                    d = d[:4] + struct.pack("<I", master_to_ours(mname, mms, struct.unpack_from("<I", d, 4)[0])) + d[8:]
                subs.append((s, d))
        edid = next((d for s, d in subs if s == "EDID"), b"").rstrip(b"\0").decode("latin-1")
        subs = [("EDID", ("CWGAR_" + edid).encode("latin-1") + b"\0") if s == "EDID" else (s, d) for s, d in subs]
        subs = list_refs_rewritten(sig, subs)
        out_records[new] = (sig, flags & ~0x20, new, tail, build_body(subs))

    # --- write the plugin
    groups = {}
    for r in kept:
        rb = record_bytes(*out_records[r.fid]) if r.fid in out_records else raw_record(r)
        groups.setdefault(r.sig, []).append(rb)
    for fid, rec in out_records.items():
        if fid not in by_fid:
            groups.setdefault(rec[0], []).append(record_bytes(*rec))
    nrec = sum(len(v) for v in groups.values())
    payload = b"".join(group(sig, b"".join(groups[sig])) for sig in TOP_ORDER if sig in groups)
    unknown = set(groups) - set(TOP_ORDER)
    if unknown:
        fail(f"no top-level slot for {unknown}")
    hsubs = [(s, struct.pack("<fiI", hver, nrec + len(groups), next_id) if s == "HEDR" else d) for s, d in hdr.subs()]
    tes4 = record_bytes("TES4", hdr.flags, hdr.fid, hdr.tail, build_body(hsubs))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(tes4 + payload)

    # --- write the SPID ini
    def form(fid):
        c = canon(fid)
        name = PLUGIN if c[0] == PLUGIN.lower() else masters[[m.lower() for m in masters].index(c[0])]
        return f"0x{c[1]:X}~{name}"

    def cform(c):
        name = PLUGIN if c[0] == PLUGIN.lower() else masters[[m.lower() for m in masters].index(c[0])]
        return f"0x{c[1]:X}~{name}"

    def edid_of(fid):
        if fid in out_records:
            return Rec(*out_records[fid][:2], fid, b"", b"", out_records[fid][4]).edid
        if fid in by_fid:
            return by_fid[fid].edid
        c = canon(fid)
        return mdb[c][2].edid if c in mdb else "?"

    def npc_name(c):
        return mdb[c][2].edid if c in mdb else "?"

    lines = [
        "; Civil War Guard Armor Replacer - Spell Perk Item Distributor rules (GENERATED by tools/spid-convert.py)",
        "; Requires Spell Perk Item Distributor 7.2 or later (outfit filters read the outfit the plugins set).",
        ";",
        "; The plugin beside this file only DEFINES the armour. These lines decide who wears it. Every form is",
        "; written as 0xID~Plugin, so no line depends on EditorIDs; the EditorID is in the comment above it.",
        ";",
        "; Format: Outfit = <outfit> | <string filters> | <form filters> | <level> | <traits> | <count> | <chance>",
        ";   form filters: ',' = any of, '+' = all of.",
        "; SPID gives an NPC the FIRST outfit line it matches, so the named NPCs (section B) come before the",
        "; general rules (section A) and need no exclusions there.",
        "",
        "; ---------------------------------------------------------------------------------------------------------",
        "; B. Named NPCs whose outfit 1.0.x set on the NPC itself (light / heavy / archer variants, officers,",
        ";    unique NPCs). The filter is the NPC (AND the outfit it starts in, where that is its own). SPID also",
        ";    matches every NPC built from a named NPC, so an NPC is named only when all of those should wear the",
        ";    same outfit; the rest get section A's version of their outfit.",
        "; ---------------------------------------------------------------------------------------------------------",
    ]

    def own_outfit_is_reliable(c):
        """True when the NPC wears its own DOFT (no 'Use Inventory' template), so its starting outfit is known."""
        if c not in mdb or mdb[c][2].sig != "NPC_":
            return False
        acbs = mdb[c][2].get("ACBS")
        return not (acbs and mdb[c][2].get("TPLT") and struct.unpack_from("<H", acbs, 18)[0] & 0x100)

    # SPID matches an NPC filter against the NPC AND its template (and, for a levelled actor, the NPC it was made
    # from and the list entry it was built on), so naming an NPC also dresses every NPC built from it. An NPC is
    # named only when every NPC built from it - directly, or through a levelled NPC list that holds it - should
    # wear the same outfit; every other NPC 1.0.x re-dressed falls back to section A (its side's / hold's armour
    # in the general variant).
    desired_all = {c: o for o, cs in npc_rules.items() for c in cs}
    templ_of = {}                       # NPC -> its TPLT target
    lvln_members = {}                   # LVLN -> NPC entries (recursive)
    for c, (mname, mms, mr) in mdb.items():
        if mr.sig == "NPC_" and mr.get("TPLT"):
            templ_of[c] = canon(master_to_ours(mname, mms, struct.unpack("<I", mr.get("TPLT"))[0]))

    def members(l, depth=0):
        if l in lvln_members:
            return lvln_members[l]
        out = set()
        if depth < 8 and l in mdb and mdb[l][2].sig == "LVLN":
            mname, mms, mr = mdb[l]
            for s_, d in mr.subs():
                if s_ == "LVLO":
                    e = canon(master_to_ours(mname, mms, struct.unpack_from("<I", d, 4)[0]))
                    out |= members(e, depth + 1) if e in mdb and mdb[e][2].sig == "LVLN" else {e}
        lvln_members[l] = out
        return out

    built_from = {}                     # NPC -> NPCs that SPID would also match through it
    for d, t in templ_of.items():
        targets = members(t) if t in mdb and mdb[t][2].sig == "LVLN" else {t}
        for t2 in targets:
            built_from.setdefault(t2, set()).add(d)

    def nameable(c):
        o = desired_all.get(c)
        return all(desired_all.get(d) == o for d in built_from.get(c, ()))

    skipped_b = []
    for outfit in list(npc_rules):
        keep = [c for c in npc_rules[outfit] if nameable(c)]
        skipped_b += [(c, outfit) for c in npc_rules[outfit] if c not in keep]
        if keep:
            npc_rules[outfit] = keep
        else:
            del npc_rules[outfit]

    # Where 1.0.x moved EVERY wearer of one vanilla outfit to the same new outfit, but some of them could not be
    # named (template NPCs), the outfit itself is the filter instead: "everyone in X gets W" - no NPC IDs at all.
    wearers = {}
    for c, (mname, mms, mr) in mdb.items():
        if mr.sig == "NPC_":
            e = effective_outfit(c, False)
            if e is not None:
                wearers.setdefault(e, []).append(c)
    desired_of = {}
    for c, o in skipped_b:
        desired_of[c] = o
    for outfit, cs in npc_rules.items():
        for c in cs:
            desired_of[c] = outfit
    rule_a2 = {}
    for c, o in skipped_b:
        x = npc_initial.get(c)
        if x is None or x in rule_a2:
            continue
        ws = wearers.get(x, [])
        if ws and all(desired_of.get(w) == o for w in ws):
            rule_a2[x] = o
    for x, o in rule_a2.items():            # those NPCs no longer need naming
        for outfit in list(npc_rules):
            npc_rules[outfit] = [c for c in npc_rules[outfit] if npc_initial.get(c) != x]
            if not npc_rules[outfit]:
                del npc_rules[outfit]

    rule_b = []
    for outfit in sorted(npc_rules, key=lambda f: edid_of(f)):
        npcs = sorted(npc_rules[outfit])
        groups = [cform(c) + ("+" + form(npc_initial[c]) if npc_initial.get(c) and own_outfit_is_reliable(c) else "")
                  for c in npcs]
        lines.append(f"; {edid_of(outfit)}: " + ", ".join(npc_name(c) for c in npcs))
        lines.append(f"Outfit = {form(outfit)}|NONE|" + ",".join(groups))
        rule_b.append({"outfit": edid_of(outfit), "npcs": [npc_name(c) for c in npcs]})

    if rule_a2:
        lines += [
            "",
            "; ---------------------------------------------------------------------------------------------------------",
            "; A2. Vanilla outfits whose every wearer 1.0.x moved to the same outfit: the outfit is the filter.",
            "; ---------------------------------------------------------------------------------------------------------",
        ]
        for x, o in sorted(rule_a2.items(), key=lambda kv: edid_of(kv[0])):
            lines.append(f"; {edid_of(o)} for wearers of {edid_of(x)} (all {len(wearers.get(x, []))} of them)")
            lines.append(f"Outfit = {form(o)}|NONE|{form(x)}")
    lines += [
        "",
        "; ---------------------------------------------------------------------------------------------------------",
        "; A. Whoever the plugins dress in a vanilla guard / soldier outfit gets this mod's version of that outfit.",
        ";    The vanilla outfit IS the scope: SPID matches it against the outfit the plugins gave the NPC, so the",
        ";    line reaches exactly the NPCs 1.0.x's outfit override reached. Nobody who wears anything else - a",
        ";    Vigilant of Stendarr (VigilantOfStendarrOutfit), a bandit, a citizen - can match.",
        "; ---------------------------------------------------------------------------------------------------------",
    ]
    rule_a = []
    for fid in a_outfits:
        users = 0
        for c, (mname, mms, mr) in mdb.items():
            d = mr.get("DOFT") if mr.sig == "NPC_" else None
            if d and master_to_ours(mname, mms, struct.unpack("<I", d)[0]) == fid:
                users += 1
        lines.append(f"; {edid_of(copies[fid])} for wearers of {edid_of(fid)}")
        lines.append(f"Outfit = {form(copies[fid])}|NONE|{form(fid)}")
        rule_a.append({"outfit": edid_of(copies[fid]), "vanilla": edid_of(fid), "vanilla_wearers": users})
    os.makedirs(os.path.dirname(os.path.abspath(a.ini)), exist_ok=True)
    with open(a.ini, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")

    report = {"kept": len(kept), "copies": len(copies), "records": nrec, "next_id": hex(next_id),
              "dropped": dropped, "rule_a": rule_a, "rule_b": rule_b,
              "b_skipped_template_npcs": [(npc_name(c), edid_of(o)) for c, o in skipped_b],
              "rule_a2": {edid_of(x): edid_of(o) for x, o in rule_a2.items()},
              "vanilla_outfit_copies_for_b": [edid_of(f) for f in vanilla_copies]}
    if a.report:
        json.dump(report, open(a.report, "w"), indent=1)
    print(f"plugin: {nrec} records ({len(kept)} kept, {len(copies)} CWGAR_ copies), next light id {next_id:#x}")
    print(f"dropped: {dropped}")
    print(f"ini: {len(rule_a)} rule-A lines, {len(rule_b)} rule-B lines ({sum(len(v) for v in npc_rules.values())} NPCs)")


if __name__ == "__main__":
    main()

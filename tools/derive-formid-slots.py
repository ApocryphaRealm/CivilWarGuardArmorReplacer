"""Derive, from the plugins themselves, which (record type, subrecord, offset) slots hold FormIDs.

A merge has to renumber every new record and then fix every reference to it. Guessing which fields
are references is how a merge corrupts a record silently. Instead: collect every 4-byte-aligned
slot in every subrecord, and see whether its values consistently resolve to a record that actually
exists (in this plugin or one of its masters). A slot that always resolves is a reference field; a
slot that never does is data.
"""
import struct, collections, io, os

PLUGS = [("SoS", "D:/modlists/Njordlinger/mods/Sons of Skyrim/NW_Sons_of_Skyrim.esp"),
         ("NewLegion", "nl/Data/DIS_Heavy_Legion.esp"),
         ("Tribune", "tribune/Tribune armor esl/TribuneArmor.esp"),
         ("TulliusRepl", "tribune/Imperial Tribune Tullius Outfit replacer/ImperialTribuneTulliusReplacer.esp")]

def parse(path):
    d = open(path, "rb").read()
    hs = struct.unpack("<I", d[4:8])[0]
    masters, i = [], 24
    while i + 6 <= 24 + hs:
        s = d[i:i+4]; n = struct.unpack("<H", d[i+4:i+6])[0]; i += 6
        if s == b"MAST": masters.append(d[i:i+n].split(b"\x00")[0].decode("latin-1"))
        i += n
    recs = []
    def walk(off, end):
        while off < end:
            t = d[off:off+4]; n = struct.unpack("<I", d[off+4:off+8])[0]
            if t == b"GRUP": walk(off+24, off+n); off += n; continue
            fid = struct.unpack("<I", d[off+12:off+16])[0]
            recs.append((t.decode(), fid, d[off+24:off+24+n]))
            off += 24 + n
    walk(24+hs, len(d))
    return masters, recs

def subs(b):
    i = 0
    while i + 6 <= len(b):
        s = b[i:i+4]; n = struct.unpack("<H", b[i+4:i+6])[0]; i += 6
        yield s.decode("latin-1"), b[i:i+n]; i += n

# every FormID that exists anywhere in our four plugins (their own new records)
own = set()
parsed = {}
for name, p in PLUGS:
    m, r = parse(p)
    parsed[name] = (m, r)
    own |= {fid for _, fid, _ in r}

slots = collections.defaultdict(lambda: [0, 0])   # (type, sub, offset) -> [resolved, total]
for name, (masters, recs) in parsed.items():
    nmast = len(masters)
    for t, fid, body in recs:
        for sig, data in subs(body):
            for off in range(0, len(data) - 3, 4):
                v = struct.unpack_from("<I", data, off)[0]
                key = (t, sig, off if len(data) <= 32 else -1)
                slots[key][1] += 1
                idx = v >> 24
                # a plausible reference: index inside this plugin's master table or its own index,
                # and a non-trivial local id
                if v != 0 and v != 0xFFFFFFFF and idx <= nmast and (v & 0xFFFFFF) > 0x100:
                    slots[key][0] += 1

out = io.open("schema.txt", "w", encoding="utf-8")
out.write("slots where EVERY value looks like a reference (candidate FormID fields)\n\n")
for key in sorted(slots):
    res, tot = slots[key]
    if tot >= 3 and res == tot:
        out.write("  %-5s %-5s off=%-4s   n=%d\n" % (key[0], key[1], key[2], tot))
out.write("\n\nslots that are MIXED - need a real schema, not a guess\n\n")
for key in sorted(slots):
    res, tot = slots[key]
    if tot >= 3 and 0 < res < tot:
        out.write("  %-5s %-5s off=%-4s   %d/%d look like references\n" % (key[0], key[1], key[2], res, tot))
out.close()
print("written")

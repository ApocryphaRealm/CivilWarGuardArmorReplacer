#!/usr/bin/env python3
r"""Assemble every mesh and texture the all-in-one mod needs, reading the Nexus downloads.

WHAT GOES IN
    * Sons of Skyrim (68656)        - Stormcloak and hold-guard armour, the Stormcloak base
    * New Legion (30468)            - the Imperial Legion replacer, including the general's set
    * Guards Armor Replacer (22671) - ONLY two holds: Winterhold, and Windhelm's SCALE set
    * Imperial Tribune Armor (54294)- General Tullius's armour

THE GUARDS ARMOR REPLACER TRICK
    The owner wants Guards Armor Replacer's Winterhold and Windhelm art on those two holds instead
    of Sons of Skyrim's own. Because this mod ships the whole asset tree itself, that needs no
    record edits at all: GAR's meshes are written UNDER SONS OF SKYRIM'S FILE NAMES, so the merged
    plugin keeps pointing exactly where it always did and simply finds different art there.

    The Windhelm set is the SCALE family - ArmorScaleLight for light and ArmorScale for heavy -
    identified from the picture on GAR's own page by matching it against Scale_Armor.dds.

WHAT IT REFUSES TO DO
    * ship a mesh whose textures are not in the package, since that renders purple in game;
    * map a GAR mesh onto a Sons of Skyrim name that does not exist, which would leave a record
      pointing at nothing;
    * finish while any download is missing.

Usage:  python tools/build-assets.py [--dry-run]
"""
import argparse
import os
import re
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
DIST = os.path.join(REPO, "dist")
DOWNLOADS = os.environ.get("CWGAR_DOWNLOADS", r"D:\modlists\Njordlinger\downloads")
SEVENZIP = [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe", "7z"]

SOURCES = {
    "sos":     ("Sons of Skyrim",         None),   # taken from the installed mod, see below
    "legion":  ("Base-30468",             ["Data\\Meshes\\Armor_Replacer\\*"]),
    "legiontx": ("Textures HD-30468", ["Data\\Textures\\*"]),
    "gar":     ("Guards Armor Replacer-22671", ["Meshes\\1_Soldier_Replacer\\Guards\\Winterhold\\*",
                                                "Meshes\\1_Soldier_Replacer\\Guards\\Windhelm\\*",
                                                "Textures\\1_Soldier_Replacer\\Guards\\*"]),
    # No pattern list: this is a .rar whose folders sit under a wrapper directory, and
    # filtering on a "meshes\*" pattern matched nothing - it silently contributed zero files.
    "tribune": ("Imperial Tribune Armor-54294", None),
}

# GAR mesh  ->  the Sons of Skyrim file it becomes. Winterhold first, then Windhelm's scale set.
GAR_MAP = {
    # --- Winterhold: SoS keeps Armor / Helmet / Shield; GAR has no Winterhold cloak, so the
    #     cloak stays Sons of Skyrim's own.
    "Winterhold/Armor/ArmorM_0.nif":          "Winterhold/ArmorM_0.nif",
    "Winterhold/Armor/ArmorM_1.nif":          "Winterhold/ArmorM_1.nif",
    "Winterhold/Armor/ArmorF_0.nif":          "Winterhold/ArmorF_0.nif",
    "Winterhold/Armor/ArmorF_1.nif":          "Winterhold/ArmorF_1.nif",
    "Winterhold/Armor/1stPersonArmorM_0.nif": "Winterhold/1stpersonArmorM_0.nif",
    "Winterhold/Armor/1stPersonArmorM_1.nif": "Winterhold/1stpersonArmorM_1.nif",
    "Winterhold/Armor/1stPersonArmorF_0.nif": "Winterhold/1stpersonArmorF_0.nif",
    "Winterhold/Armor/1stPersonArmorF_1.nif": "Winterhold/1stpersonArmorF_1.nif",
    "Winterhold/Armor/Armor_Gnd.nif":         "Winterhold/Armor_Gnd.nif",
    "Winterhold/Armor/Helmet_M.nif":          "Winterhold/Helmet_M.nif",
    "Winterhold/Armor/Helmet_F.nif":          "Winterhold/Helmet_F.nif",
    "Winterhold/Armor/Helmet_MA.nif":         "Winterhold/Helmet_MA.nif",
    "Winterhold/Armor/Helmet_FA.nif":         "Winterhold/Helmet_FA.nif",
    "Winterhold/Armor/Helmet_MK.nif":         "Winterhold/Helmet_MK.nif",
    "Winterhold/Armor/Helmet_FK.nif":         "Winterhold/Helmet_FK.nif",
    "Winterhold/Armor/Helmet_O.nif":          "Winterhold/Helmet_MO.nif",
    "Winterhold/Armor/Helmet_Gnd.nif":        "Winterhold/Helmet_Gnd.nif",
    "Winterhold/Armor/shield.nif":            "Winterhold/ShieldHeavy.nif",
    # --- Windhelm, the SCALE set: heavy = ArmorScale, light = ArmorScaleLight
    "Windhelm/Armor/ArmorScaleM_0.nif":       "Windhelm/WindhelmArmorHeavyM_0.nif",
    "Windhelm/Armor/ArmorScaleM_1.nif":       "Windhelm/WindhelmArmorHeavyM_1.nif",
    "Windhelm/Armor/ArmorScaleF_0.nif":       "Windhelm/WindhelmArmorHeavyF_0.nif",
    "Windhelm/Armor/ArmorScaleF_1.nif":       "Windhelm/WindhelmArmorHeavyF_1.nif",
    "Windhelm/Armor/ArmorScale_Gnd.nif":      "Windhelm/WindhelmArmorHeavy_Gnd.nif",
    "Windhelm/Armor/ArmorScaleLightM_0.nif":  "Windhelm/WindhelmArmorM_0.nif",
    "Windhelm/Armor/ArmorScaleLightM_1.nif":  "Windhelm/WindhelmArmorM_1.nif",
    "Windhelm/Armor/ArmorScaleLightF_0.nif":  "Windhelm/WindhelmArmorF_0.nif",
    "Windhelm/Armor/ArmorScaleLightF_1.nif":  "Windhelm/WindhelmArmorF_1.nif",
    "Windhelm/Armor/ArmorScaleLight_Gnd.nif": "Windhelm/WindhelmArmor_Gnd.nif",
}

SOS_MESH_ROOT = os.path.join("Meshes", "NordWar", "SonsOfSkyrim")
TEXPAT = re.compile(rb"[Tt]extures.{1,180}?\.dds")
VANILLA_TEX = ("textures\\actors\\", "textures\\blood\\", "textures\\cubemaps\\eyecubemap")


def fail(msg):
    raise SystemExit("build-assets: " + msg)


def sevenzip():
    for c in SEVENZIP:
        if os.path.isfile(c):
            return c
        if shutil.which(c):
            return shutil.which(c)
    fail("7-Zip not found")


def find(fragment):
    for f in sorted(os.listdir(DOWNLOADS)):
        if fragment.lower() in f.lower() and f.lower().endswith((".7z", ".zip", ".rar")):
            return os.path.join(DOWNLOADS, f)
    fail("no download matching '%s' in %s" % (fragment, DOWNLOADS))


def extract(fragment, patterns, dest):
    os.makedirs(dest, exist_ok=True)
    args = [sevenzip(), "x", "-y", "-o" + dest, find(fragment)] + (patterns or []) + ["-r"]
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        fail("7-Zip failed on %s:\n%s" % (fragment, p.stdout + p.stderr))
    data = os.path.join(dest, "Data")
    if os.path.isdir(data):
        for n in os.listdir(data):
            t = os.path.join(dest, n)
            if os.path.isdir(t):
                for dp, _, fns in os.walk(os.path.join(data, n)):
                    for fn in fns:
                        s = os.path.join(dp, fn)
                        q = os.path.join(t, os.path.relpath(s, os.path.join(data, n)))
                        os.makedirs(os.path.dirname(q), exist_ok=True)
                        shutil.move(s, q)
            else:
                shutil.move(os.path.join(data, n), t)
        shutil.rmtree(data, ignore_errors=True)
    return dest


def ci(root, rel):
    cur = root
    for part in rel.replace("\\", "/").split("/"):
        if not part:
            continue
        if not os.path.isdir(cur):
            return None
        m = next((e for e in os.listdir(cur) if e.lower() == part.lower()), None)
        if m is None:
            return None
        cur = os.path.join(cur, m)
    return cur


def copy_tree(src, dst, counter):
    for dp, _, fns in os.walk(src):
        for fn in fns:
            s = os.path.join(dp, fn)
            d = os.path.join(dst, os.path.relpath(s, src))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            counter[0] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    work = os.path.join(REPO, "_assets")
    shutil.rmtree(work, ignore_errors=True)
    if not a.dry_run:
        shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(work, exist_ok=True)

    n = [0]
    report = []

    # --- Sons of Skyrim: taken from the installed mod, which is the copy the owner uses
    sos = r"D:\modlists\Njordlinger\mods\Sons of Skyrim"
    if not os.path.isdir(sos):
        fail("Sons of Skyrim is not installed at %s, and it is the base of this mod" % sos)
    before = n[0]
    if not a.dry_run:
        for sub in ("Meshes", "Textures"):
            s = ci(sos, sub)
            if s:
                copy_tree(s, os.path.join(DIST, sub), n)
    report.append(("Sons of Skyrim", n[0] - before))

    # --- New Legion meshes and textures
    for key in ("legion", "legiontx"):
        frag, pats = SOURCES[key]
        d = extract(frag, pats, os.path.join(work, key))
        before = n[0]
        if not a.dry_run:
            for sub in ("Meshes", "Textures"):
                s = ci(d, sub)
                if s:
                    copy_tree(s, os.path.join(DIST, sub), n)
        report.append((frag, n[0] - before))

    # --- Imperial Tribune
    frag, pats = SOURCES["tribune"]
    d = extract(frag, pats, os.path.join(work, "tribune"))
    root = None
    for dp, dn, fns in os.walk(d):
        if any(x.lower() == "meshes" for x in dn) and any(x.lower() == "textures" for x in dn):
            root = dp
            break
    if root is None:
        fail("the Imperial Tribune download did not yield a folder holding both meshes and textures")
    before = n[0]
    if not a.dry_run:
        for sub in ("meshes", "textures"):
            s = ci(root, sub)
            if s:
                copy_tree(s, os.path.join(DIST, sub.capitalize()), n)
    report.append((frag, n[0] - before))

    # --- Guards Armor Replacer: two holds, written under Sons of Skyrim's names
    frag, pats = SOURCES["gar"]
    gar = extract(frag, pats, os.path.join(work, "gar"))
    gmesh = ci(gar, os.path.join("Meshes", "1_Soldier_Replacer", "Guards"))
    gtex = ci(gar, os.path.join("Textures", "1_Soldier_Replacer", "Guards"))
    if not gmesh or not gtex:
        fail("Guards Armor Replacer did not yield both its Guards meshes and its Guards textures")

    swapped, wanted = 0, set()
    for src, dst in sorted(GAR_MAP.items()):
        s = ci(gmesh, src)
        if s is None:
            fail("Guards Armor Replacer has no '%s' - its layout has changed" % src)
        target = os.path.join(DIST, SOS_MESH_ROOT, dst.replace("/", os.sep))
        if not a.dry_run and not os.path.isfile(target):
            fail("'%s' is not a Sons of Skyrim mesh - a record would be left pointing at nothing"
                 % dst)
        for m in TEXPAT.findall(open(s, "rb").read()):
            v = m.decode("latin-1").replace("/", "\\").lower()
            if not v.startswith(VANILLA_TEX):
                wanted.add(os.path.basename(v))
        if not a.dry_run:
            shutil.copy2(s, target)
        swapped += 1

    tex_copied = 0
    if not a.dry_run:
        dstdir = os.path.join(DIST, "Textures", "1_Soldier_Replacer", "Guards")
        os.makedirs(dstdir, exist_ok=True)
        for dp, _, fns in os.walk(gtex):
            for fn in fns:
                if fn.lower() in wanted:
                    shutil.copy2(os.path.join(dp, fn), os.path.join(dstdir, fn))
                    tex_copied += 1
    report.append(("Guards Armor Replacer (2 holds)", swapped + tex_copied))

    shutil.rmtree(work, ignore_errors=True)
    total = sum(len(f) for _, _, f in os.walk(DIST)) if os.path.isdir(DIST) else 0
    print("assets assembled%s" % ("  (dry run)" if a.dry_run else ""))
    for name, c in report:
        print("  %-42s %d files" % (name[:42], c))
    print("  GAR meshes over Sons of Skyrim names  %d, plus %d textures" % (swapped, tex_copied))
    print("  files in dist ......................... %d" % total)


if __name__ == "__main__":
    main()

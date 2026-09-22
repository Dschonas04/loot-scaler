#!/usr/bin/env python3
"""Generate a datapack that scales ore and mob loot.

    python3 loot_scaler.py --server /srv/mc/versions/26.2/server-26.2.jar \
                           --mods /srv/mc/mods \
                           --out /srv/mc/world/datapacks/loot-scaler

The datapack is built from the loot tables that are already installed on your
server: they are read out of the server jar and the mod jars, get a chance
condition applied, and are written out again under the same names. Nothing from
the game itself is shipped with this tool — it only ever rewrites what is
already on your disk.

How the scaling works
---------------------
Loot tables do not carry a "rate" that could be multiplied, so the multiplier
becomes a chance: at 0.7 every pool rolls only 7 times out of 10. Over a mining
session or a mob farm that averages out to 70 % of the loot, while a single drop
stays all-or-nothing.

For ores only the *item* entries are scaled. The silk touch branch, which hands
back the ore block itself, is left alone — scaling it would make blocks vanish
into thin air 30 % of the time. Fortune still works, on the rolls that happen.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile

ERZ_MUSTER = re.compile(r"^data/([a-z0-9_.-]+)/loot_table/blocks/[a-z0-9_/]*ore[a-z0-9_/]*\.json$")
MOB_MUSTER = re.compile(r"^data/([a-z0-9_.-]+)/loot_table/entities/[a-z0-9_/]+\.json$")
# Ores that do not have "ore" in their name.
ZUSATZ_ERZE = re.compile(r"^data/([a-z0-9_.-]+)/loot_table/blocks/(ancient_debris|gilded_blackstone)\.json$")


def lies_konfiguration(pfad: str) -> dict:
    """Read the key = value file. Unknown keys are reported, not ignored."""
    werte = {"ores": 1.0, "mobs": 1.0, "include_mods": True, "exclude": set(), "tables": {}}
    bekannt = {"ores", "mobs", "include_mods", "exclude"}
    with open(pfad, encoding="utf-8") as datei:
        for nummer, zeile in enumerate(datei, start=1):
            zeile = zeile.split("#", 1)[0].strip()
            if not zeile:
                continue
            if "=" not in zeile:
                sys.exit(f"{pfad}:{nummer}: expected 'key = value', got {zeile!r}")
            schluessel, wert = (teil.strip() for teil in zeile.split("=", 1))
            if schluessel.startswith("table."):
                werte["tables"][schluessel[len("table."):].strip()] = faktor(wert, pfad, nummer)
            elif schluessel == "exclude":
                werte["exclude"] = {t.strip() for t in wert.split(",") if t.strip()}
            elif schluessel == "include_mods":
                werte["include_mods"] = wert.lower() in ("true", "yes", "1", "on")
            elif schluessel in bekannt:
                werte[schluessel] = faktor(wert, pfad, nummer)
            else:
                sys.exit(f"{pfad}:{nummer}: unknown setting {schluessel!r}")
    return werte


def faktor(wert: str, pfad: str, nummer: int) -> float:
    try:
        zahl = float(wert)
    except ValueError:
        sys.exit(f"{pfad}:{nummer}: {wert!r} is not a number")
    if not 0.0 <= zahl <= 1.0:
        sys.exit(f"{pfad}:{nummer}: {zahl} is outside 0.0 … 1.0")
    return zahl


def tabellenname(pfad: str) -> str:
    """data/minecraft/loot_table/blocks/iron_ore.json -> minecraft:blocks/iron_ore"""
    teile = pfad.split("/")
    return f"{teile[1]}:{'/'.join(teile[3:])[:-len('.json')]}"


def bedingung(faktor: float) -> dict:
    return {"condition": "minecraft:random_chance", "chance": faktor}


def skaliere_erz(tabelle: dict, blockid: str, faktor: float) -> int:
    """Chance on every item entry except the block itself (the silk touch branch)."""
    berührt = 0
    for topf in tabelle.get("pools", []):
        for eintrag in topf.get("entries", []):
            for knoten in eintrag.get("children", [eintrag]):
                if knoten.get("type") == "minecraft:item" and knoten.get("name") != blockid:
                    knoten.setdefault("conditions", []).append(bedingung(faktor))
                    berührt += 1
    return berührt


def skaliere_mob(tabelle: dict, faktor: float) -> int:
    """Chance on every pool, so drops and equipment are scaled alike."""
    toepfe = tabelle.get("pools", [])
    for topf in toepfe:
        topf.setdefault("conditions", []).append(bedingung(faktor))
    return len(toepfe)


def quellen(server: str, mods: str | None, mit_mods: bool) -> list[str]:
    liste = [server]
    if mit_mods and mods:
        liste += sorted(
            os.path.join(mods, name) for name in os.listdir(mods) if name.endswith(".jar")
        )
    return liste


def baue(konf: dict, server: str, mods: str | None, ziel: str) -> dict:
    zahlen = {"ores": 0, "mobs": 0, "skipped": 0, "excluded": 0}
    geschrieben: set[str] = set()
    for quelle in quellen(server, mods, konf["include_mods"]):
        try:
            archiv = zipfile.ZipFile(quelle)
        except (zipfile.BadZipFile, OSError) as fehler:
            print(f"  skipping {os.path.basename(quelle)}: {fehler}", file=sys.stderr)
            continue
        for eintrag in archiv.namelist():
            erz = ERZ_MUSTER.match(eintrag) or ZUSATZ_ERZE.match(eintrag)
            mob = MOB_MUSTER.match(eintrag)
            if not (erz or mob) or eintrag in geschrieben:
                continue
            name = tabellenname(eintrag)
            if name in konf["exclude"]:
                zahlen["excluded"] += 1
                continue
            wie_viel = konf["tables"].get(name, konf["ores"] if erz else konf["mobs"])
            if wie_viel >= 1.0:
                continue
            try:
                tabelle = json.loads(archiv.read(eintrag))
            except (ValueError, UnicodeDecodeError):
                zahlen["skipped"] += 1  # broken table in that jar, leave it to the game
                continue
            if erz:
                blockid = f"{erz.group(1)}:{os.path.basename(eintrag)[: -len('.json')]}"
                treffer = skaliere_erz(tabelle, blockid, wie_viel)
            else:
                treffer = skaliere_mob(tabelle, wie_viel)
            if not treffer:
                zahlen["skipped"] += 1
                continue
            pfad = os.path.join(ziel, eintrag)
            os.makedirs(os.path.dirname(pfad), exist_ok=True)
            with open(pfad, "w", encoding="utf-8") as datei:
                json.dump(tabelle, datei, ensure_ascii=False, indent=1)
            geschrieben.add(eintrag)
            zahlen["ores" if erz else "mobs"] += 1
    return zahlen


def schreibe_mcmeta(ziel: str, konf: dict, format_bereich: list[list[int]]) -> None:
    beschreibung = f"loot-scaler: ores {konf['ores']}, mobs {konf['mobs']}"
    os.makedirs(ziel, exist_ok=True)
    with open(os.path.join(ziel, "pack.mcmeta"), "w", encoding="utf-8") as datei:
        json.dump({"pack": {"description": beschreibung,
                            "min_format": format_bereich[0],
                            "max_format": format_bereich[1]}}, datei, indent=1)


def pack_format(server: str) -> list[list[int]]:
    """Take the data pack format straight from the server jar it will run on."""
    try:
        with zipfile.ZipFile(server) as archiv:
            fassung = json.loads(archiv.read("version.json"))["pack_version"]
        return [[fassung["data_major"], 0], [fassung["data_major"], fassung.get("data_minor", 0)]]
    except (KeyError, OSError, ValueError, zipfile.BadZipFile):
        return [[1, 0], [9999, 0]]


def main() -> None:
    leser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    leser.add_argument("--server", required=True, help="path to the server jar")
    leser.add_argument("--mods", help="path to the mods directory")
    leser.add_argument("--out", required=True, help="datapack directory to write")
    leser.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "loot-scaler.conf"))
    args = leser.parse_args()

    konf = lies_konfiguration(args.config)
    if konf["ores"] >= 1.0 and konf["mobs"] >= 1.0 and not konf["tables"]:
        sys.exit("nothing to do: every multiplier is 1.0")

    zahlen = baue(konf, args.server, args.mods, args.out)
    schreibe_mcmeta(args.out, konf, pack_format(args.server))
    print(f"ores {zahlen['ores']}, mobs {zahlen['mobs']}, "
          f"excluded {zahlen['excluded']}, unreadable {zahlen['skipped']}")
    print(f"written to {args.out} — run /reload on the server, or restart it")


if __name__ == "__main__":
    main()

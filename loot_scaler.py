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
Amounts are scaled, not chances. A pool that always dropped something keeps
dropping something -- mining a diamond never comes up empty. What shrinks is

  * the stack size of ores that give several items (redstone, lapis, copper),
  * the Fortune bonus on ores, through ore_fortune,
  * the stack size of everything a mob drops.

Ores that give exactly one item are already at the minimum, so only their
Fortune bonus changes. Silk touch is never touched: it hands back the block.
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
    werte = {"ores": 1.0, "ore_fortune": 1.0, "mobs": 1.0, "never_zero": True,
             "include_mods": True, "exclude": set(), "tables": {}}
    bekannt = {"ores", "ore_fortune", "mobs", "include_mods", "exclude"}
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
            elif schluessel in ("include_mods", "never_zero"):
                werte[schluessel] = wert.lower() in ("true", "yes", "1", "on")
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


def skaliere_zahl(zahl: float, faktor: float, mindestens_eins: bool) -> float:
    """Scale an amount and keep it sane: whole numbers stay whole numbers."""
    neu = zahl * faktor
    if zahl >= 1 and mindestens_eins:
        neu = max(1.0, neu)
    neu = round(neu, 2)
    return int(neu) if float(neu).is_integer() else neu


def skaliere_anzahl(wert, faktor: float, mindestens_eins: bool):
    """Scale whatever a loot table uses as a count: a number or a provider."""
    if isinstance(wert, (int, float)):
        return skaliere_zahl(wert, faktor, mindestens_eins)
    if not isinstance(wert, dict):
        return wert
    art = wert.get("type", "minecraft:constant")
    if art.endswith("constant") and "value" in wert:
        wert["value"] = skaliere_zahl(wert["value"], faktor, mindestens_eins)
    elif art.endswith("uniform"):
        for rand in ("min", "max"):
            if isinstance(wert.get(rand), (int, float)):
                wert[rand] = skaliere_zahl(wert[rand], faktor, mindestens_eins and rand == "min")
    elif art.endswith("binomial") and isinstance(wert.get("n"), (int, float)):
        wert["n"] = skaliere_zahl(wert["n"], faktor, False)
    elif art.endswith("uniform_bonus_count") or art.endswith("score"):
        pass
    return wert


def skaliere_funktionen(knoten: dict, faktor: float, fortune: float, nie_null: bool) -> int:
    """Rewrite set_count and the Fortune bonus of one entry."""
    berührt = 0
    for funktion in knoten.get("functions", []):
        name = funktion.get("function", "")
        if name.endswith("set_count") and "count" in funktion and faktor < 1.0:
            funktion["count"] = skaliere_anzahl(funktion["count"], faktor,
                                                nie_null and not funktion.get("add"))
            berührt += 1
        elif name.endswith("apply_bonus") and fortune < 1.0:
            # ore_drops multiplies the drop by the Fortune level; uniform_bonus_count
            # adds at most level * multiplier, so the bonus can be dialled down.
            if funktion.get("formula", "").endswith("ore_drops"):
                funktion["formula"] = "minecraft:uniform_bonus_count"
                funktion["parameters"] = {"bonusMultiplier": round(fortune, 2)}
                berührt += 1
            elif funktion.get("formula", "").endswith("uniform_bonus_count"):
                parameter = funktion.setdefault("parameters", {"bonusMultiplier": 1})
                parameter["bonusMultiplier"] = round(
                    parameter.get("bonusMultiplier", 1) * fortune, 2)
                berührt += 1
    return berührt


def skaliere_erz(tabelle: dict, blockid: str, faktor: float, fortune: float, nie_null: bool) -> int:
    """Ores: amounts and Fortune, but never the silk touch branch."""
    berührt = 0
    for topf in tabelle.get("pools", []):
        for eintrag in topf.get("entries", []):
            for knoten in eintrag.get("children", [eintrag]):
                if knoten.get("type") != "minecraft:item" or knoten.get("name") == blockid:
                    continue
                berührt += skaliere_funktionen(knoten, faktor, fortune, nie_null)
    return berührt


def skaliere_mob(tabelle: dict, faktor: float, nie_null: bool) -> int:
    """Mobs: the amount of every item they drop."""
    berührt = 0
    for topf in tabelle.get("pools", []):
        if faktor < 1.0 and isinstance(topf.get("rolls"), dict):
            topf["rolls"] = skaliere_anzahl(topf["rolls"], faktor, nie_null)
        for eintrag in topf.get("entries", []):
            for knoten in eintrag.get("children", [eintrag]):
                berührt += skaliere_funktionen(knoten, faktor, 1.0, nie_null)
    return berührt


def quellen(server: str, mods: str | None, mit_mods: bool) -> list[str]:
    liste = [server]
    if mit_mods and mods:
        liste += sorted(
            os.path.join(mods, name) for name in os.listdir(mods) if name.endswith(".jar")
        )
    return liste


def baue(konf: dict, server: str, mods: str | None, ziel: str) -> dict:
    zahlen = {"ores": 0, "mobs": 0, "unchanged": 0, "unreadable": 0, "excluded": 0}
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
            eigen = konf["tables"].get(name)
            wie_viel = eigen if eigen is not None else (konf["ores"] if erz else konf["mobs"])
            fortune = eigen if eigen is not None else konf["ore_fortune"]
            if wie_viel >= 1.0 and (not erz or fortune >= 1.0):
                continue
            try:
                tabelle = json.loads(archiv.read(eintrag))
            except (ValueError, UnicodeDecodeError):
                zahlen["unreadable"] += 1  # broken table in that jar, leave it to the game
                continue
            if erz:
                blockid = f"{erz.group(1)}:{os.path.basename(eintrag)[: -len('.json')]}"
                treffer = skaliere_erz(tabelle, blockid, wie_viel, fortune, konf["never_zero"])
            else:
                treffer = skaliere_mob(tabelle, wie_viel, konf["never_zero"])
            if not treffer:
                zahlen["unchanged"] += 1  # nothing to scale: fixed single drop
                continue
            pfad = os.path.join(ziel, eintrag)
            os.makedirs(os.path.dirname(pfad), exist_ok=True)
            with open(pfad, "w", encoding="utf-8") as datei:
                json.dump(tabelle, datei, ensure_ascii=False, indent=1)
            geschrieben.add(eintrag)
            zahlen["ores" if erz else "mobs"] += 1
    return zahlen


def schreibe_mcmeta(ziel: str, konf: dict, format_bereich: list[list[int]]) -> None:
    beschreibung = (f"loot-scaler: ores {konf['ores']}, fortune {konf['ore_fortune']}, "
                    f"mobs {konf['mobs']}")
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
    if (konf["ores"] >= 1.0 and konf["mobs"] >= 1.0 and konf["ore_fortune"] >= 1.0
            and not konf["tables"]):
        sys.exit("nothing to do: every multiplier is 1.0")

    zahlen = baue(konf, args.server, args.mods, args.out)
    schreibe_mcmeta(args.out, konf, pack_format(args.server))
    print(f"scaled: {zahlen['ores']} ore tables, {zahlen['mobs']} mob tables — "
          f"left as they were: {zahlen['unchanged']} (nothing to scale), "
          f"{zahlen['excluded']} excluded, {zahlen['unreadable']} unreadable")
    print(f"written to {args.out} — run /reload on the server, or restart it")


if __name__ == "__main__":
    main()

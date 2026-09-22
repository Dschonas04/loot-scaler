# loot-scaler

Make ores and mobs drop less, so a world lasts longer.

Minecraft has a game rule for almost everything, but not for "how much does an iron ore give". This is a small Python script that writes a data pack for you: you set two numbers in a config file, drop the result into `world/datapacks`, and reload.

It works with modded servers as well, because it does not carry a list of loot tables around — it reads the tables that are actually installed on your server, out of the server jar and out of every mod jar, and rewrites those.

## Use it

```bash
git clone https://github.com/Dschonas04/loot-scaler
cd loot-scaler
$EDITOR loot-scaler.conf

python3 loot_scaler.py \
  --server /path/to/server/versions/1.21.9/server-1.21.9.jar \
  --mods   /path/to/server/mods \
  --out    /path/to/server/world/datapacks/loot-scaler
```

Then, on the server console:

```
/reload
```

Python 3.9 or newer, no dependencies. Works on Fabric, NeoForge, Forge, Paper, and vanilla — it only produces a data pack.

## Configure it

`loot-scaler.conf`, one `key = value` per line:

```properties
ores = 0.7           # ores still drop 70 % of what they used to
mobs = 0.7           # same for everything a creature drops
include_mods = true  # scale the loot tables of mods too
exclude = minecraft:entities/ender_dragon, minecraft:entities/wither

table.minecraft:blocks/ancient_debris = 0.5   # a single table, harsher
table.minecraft:entities/enderman = 1.0       # a single table, untouched
```

Every value is a multiplier between 0 and 1, not a percentage. `1.0` keeps the vanilla rate, `0` drops nothing.

## How it scales

A loot table has no "rate" to multiply, so the multiplier becomes a chance: at `0.7`, a pool rolls 7 times out of 10. A single ore is therefore still all-or-nothing, but a mining trip or a mob farm averages out at 70 %.

Two details that matter in play:

- **Silk touch keeps working.** For ores, only the item entries are scaled, never the branch that hands back the ore block itself. Scaling that one would make blocks disappear into nothing three times out of ten.
- **Fortune keeps working**, on the rolls that do happen.

Experience is not part of loot tables and stays as it is. Chests, fishing and structure loot are untouched — this is about ores and mobs.

## What it does not ship

No game files. Loot tables belong to Mojang and to the mod authors, so this repository contains the generator only; the data pack is built on your machine from your own installation. That also means the pack always matches your versions.

## Rebuild after an update

Updating the game or a mod can change loot tables. Run the script again with the new jars, then `/reload`. Old copies of tables that no longer exist do no harm, but a fresh build keeps the pack honest — delete the output directory first if you want it clean.

## License

MIT, see [LICENSE](LICENSE).

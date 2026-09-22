# loot-scaler

Make ores and mobs drop less, so a world lasts longer.

Minecraft has a game rule for almost everything, but not for "how much does an iron ore give". This is a small Python script that writes a data pack for you: you set two numbers in a config file, drop the result into `world/datapacks`, and reload.

It works with modded servers as well, because it does not carry a list of loot tables around — it reads the tables that are actually installed on your server, out of the server jar and out of every mod jar, and rewrites those.

Amounts are scaled, not chances: a block or a mob that always dropped something still always drops something.

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
ores = 0.7         # ores that drop several items keep 70 % of their stack
ore_fortune = 0.7  # how much of the Fortune bonus on ores remains
mobs = 0.7         # same for everything a creature drops
never_zero = true  # a drop that always happened still always happens
include_mods = true
exclude = minecraft:entities/ender_dragon, minecraft:entities/wither

table.minecraft:blocks/ancient_debris = 0.5   # a single table, harsher
table.minecraft:entities/enderman = 1.0       # a single table, untouched
```

Every value is a multiplier between 0 and 1, not a percentage. `1.0` keeps the vanilla rate.

## How it scales

**Amounts, never chances.** This is the part that matters in play: mining a diamond always gives a diamond. What shrinks is how much comes out of the things that give more than one:

| | vanilla | at 0.7 |
|---|---|---|
| Iron, diamond, coal, gold, emerald | 1 | 1, with a smaller Fortune bonus |
| Redstone ore | 4–5 | 3–4 |
| Cow | ~3 items | ~2 items |
| Zombie | 0–2 rotten flesh | 0–1 |

Ores that give a single item are already at the minimum, so there `ore_fortune` is the only dial: Fortune still pays off, it just pays less. Under the hood the `ore_drops` formula, which multiplies the drop by the enchantment level, becomes a bonus count with your multiplier.

Silk touch is never scaled — it hands back the block itself, and scaling that would make blocks disappear.

Experience is not part of loot tables and stays as it is. Chests, fishing and structure loot are untouched: this is about ores and mobs.

Measured on a modded 1.21-era server at `0.7`, 150 rolls each: iron ore 1.00 items per block (unchanged, as intended), redstone ore 3.5 instead of 4.5, cow 2.0 instead of 3.0.

## What it does not ship

No game files. Loot tables belong to Mojang and to the mod authors, so this repository contains the generator only; the data pack is built on your machine from your own installation. That also means the pack always matches your versions.

## Rebuild after an update

Updating the game or a mod can change loot tables. Run the script again with the new jars, then `/reload`. Old copies of tables that no longer exist do no harm, but a fresh build keeps the pack honest — delete the output directory first if you want it clean.

## License

MIT, see [LICENSE](LICENSE).

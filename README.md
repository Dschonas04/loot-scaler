# Loot Scaler — a Minecraft mod

**Fabric mod. Ores and mobs give less, so a world lasts longer.**

For Minecraft 1.21+ on Fabric, server or single player. No Fabric API, no dependencies.

Drop the jar into `mods`, set two numbers in `config/loot-scaler.properties`, done. Modded ores and mobs are covered out of the box, because the mod carries no list of loot tables — it sits in the code path that every loot table goes through.

```properties
ores = 0.7         # keep 70 % of the extra items an ore gives
mobs = 0.7         # keep 70 % of what a creature drops
never_zero = true  # a drop of one never becomes nothing
debug = false      # log every scaled drop
```

## Amounts, never chances

This is the part that matters in play: **mining a single diamond always gives a diamond.** The mod never rolls a die on whether a drop happens — it only makes the piles smaller:

| | vanilla | at 0.7 | measured |
|---|---|---|---|
| Iron, diamond, coal, gold, emerald | 1 | 1, with a smaller Fortune bonus | 1.00 |
| Redstone ore | 4–5 | 1 + 70 % of the rest | 3.45 |
| Lapis ore | 4–9 | 1 + 70 % of the rest | 4.88 |
| Cow | ~3 items | 70 % | 2.26 |
| Zombie | ~1.1 items | 70 % | 0.80 |

Numbers from 120 rolls each on a modded 26.2 server.

For **ores** the first item is untouchable and only the surplus is scaled — the Fortune bonus, and the ores that give several items at once. For **mobs** the amount is scaled outright, since those are ranges anyway; `never_zero` keeps a guaranteed drop guaranteed.

Fractions are rounded with the loot context's own random source: 1.4 items means "one, and a second one four times out of ten", not a silently swallowed remainder.

Untouched: experience, silk touch, chest and fishing loot, and block drops that are not ores.

## Install

1. Fabric Loader 0.19 or newer, Minecraft 1.21 or newer.
2. Put `loot-scaler-<version>.jar` into `mods/`. Server side is enough for multiplayer; in single player it goes into your own mods folder.
3. Start once. The config is written to `config/loot-scaler.properties` with comments.
4. Change the numbers, restart. No Fabric API needed.

## Build the mod yourself

Minecraft 26.2 ships with readable class names, so this is a plain Gradle build against the server jar — no mappings, no remapping, no Loom:

```bash
gradle build -Pminecraft_jar=/path/to/server-26.2.jar
```

The jar lands in `build/libs/`. On older versions, which are obfuscated, you need a Loom setup with mappings instead; the mixin itself targets `LootPool#addRandomItems`, which has been stable for a long time.

## How it works

One mixin, one wrapper. Every loot pool writes its items into a consumer; the mod puts itself in front of that consumer and rewrites the stack sizes on the way through. Whether something counts as an ore or a mob is decided from the loot context — a block state means ore (by its id), a living entity means mob — so no loot table is ever edited and mod content is covered automatically.

## License

MIT, see [LICENSE](LICENSE).

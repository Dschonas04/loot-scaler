# Data pack generator

The fallback for servers where you cannot install mods. It reads the loot tables that are installed — out of the server jar and every mod jar — rewrites the amounts, and writes a data pack.

```bash
$EDITOR loot-scaler.conf
python3 loot_scaler.py \
  --server /path/to/server/versions/26.2/server-26.2.jar \
  --mods   /path/to/server/mods \
  --out    /path/to/server/world/datapacks/loot-scaler
```

Then `/reload` on the server console. Python 3.9 or newer, no dependencies.

Two differences to the mod: the pack has to be rebuilt after every game or mod update, and loot that a mod adds at runtime rather than through a table stays untouched.

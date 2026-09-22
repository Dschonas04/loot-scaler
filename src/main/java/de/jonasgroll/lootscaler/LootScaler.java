package de.jonasgroll.lootscaler;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.loader.api.FabricLoader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class LootScaler implements ModInitializer {

    public static final String ID = "loot-scaler";
    public static final Logger LOG = LoggerFactory.getLogger("Loot Scaler");

    private static Einstellungen einstellungen = new Einstellungen();

    public static Einstellungen einstellungen() {
        return einstellungen;
    }

    @Override
    public void onInitialize() {
        einstellungen = Einstellungen.lies(
                FabricLoader.getInstance().getConfigDir().resolve(ID + ".properties"));
        if (einstellungen.untaetig()) {
            LOG.info("both multipliers are 1.0 — loot stays vanilla");
        } else {
            LOG.info("ores at {}, mobs at {}", einstellungen.ores, einstellungen.mobs);
        }
    }
}

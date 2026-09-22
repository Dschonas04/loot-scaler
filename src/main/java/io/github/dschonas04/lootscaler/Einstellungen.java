package io.github.dschonas04.lootscaler;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;

/**
 * The contents of {@code config/loot-scaler.properties}.
 *
 * <p>Written with comments on first start, read again on every server start. Values are
 * multipliers, not percentages: {@code 1.0} is vanilla, {@code 0.7} keeps 70 percent.
 */
public final class Einstellungen {

    /** How much of an ore's extra items — the Fortune bonus and multi-item ores — remains. */
    public double ores = 0.7;

    /** How much of everything a creature drops remains. */
    public double mobs = 0.7;

    /** Keep at least one item whenever the unscaled drop was at least one. */
    public boolean neverZero = true;

    /** Log every scaled drop. Noisy; for checking that the numbers do what you meant. */
    public boolean debug = false;

    private static final String VORLAGE = """
            # Loot Scaler — how much loot ores and mobs still give.
            #
            # Every value is a multiplier, not a percentage: 1.0 is vanilla, 0.7 keeps 70 percent,
            # 0.0 removes the scaled part entirely. Amounts are scaled, never the chance to drop:
            # an ore that always gave something still always gives something.

            # Ores. The first item of a drop is always kept, so a single diamond stays a diamond.
            # What this scales is everything on top: the Fortune bonus, and ores that give several
            # items at once such as redstone, lapis and copper.
            ores = %s

            # Mobs. Scales the amount of everything a creature drops, its equipment included.
            mobs = %s

            # Never let scaling turn a drop of one into nothing.
            never_zero = %s

            # Write a log line for every scaled drop.
            debug = %s
            """;

    public static Einstellungen lies(Path pfad) {
        Einstellungen werte = new Einstellungen();
        if (!Files.exists(pfad)) {
            werte.schreibe(pfad);
            return werte;
        }
        try {
            for (String zeile : Files.readAllLines(pfad)) {
                int raute = zeile.indexOf('#');
                if (raute >= 0) {
                    zeile = zeile.substring(0, raute);
                }
                int gleich = zeile.indexOf('=');
                if (gleich < 0) {
                    continue;
                }
                String schluessel = zeile.substring(0, gleich).trim().toLowerCase(Locale.ROOT);
                String wert = zeile.substring(gleich + 1).trim();
                switch (schluessel) {
                    case "ores" -> werte.ores = zahl(wert, werte.ores);
                    case "mobs" -> werte.mobs = zahl(wert, werte.mobs);
                    case "never_zero" -> werte.neverZero = List.of("true", "yes", "1", "on")
                            .contains(wert.toLowerCase(Locale.ROOT));
                    case "debug" -> werte.debug = List.of("true", "yes", "1", "on")
                            .contains(wert.toLowerCase(Locale.ROOT));
                    default -> LootScaler.LOG.warn("unknown setting '{}' in {}", schluessel, pfad);
                }
            }
        } catch (IOException fehler) {
            LootScaler.LOG.error("could not read {}, using defaults: {}", pfad, fehler.getMessage());
        }
        return werte;
    }

    private static double zahl(String wert, double ersatz) {
        try {
            double zahl = Double.parseDouble(wert);
            if (zahl < 0.0 || zahl > 1.0) {
                LootScaler.LOG.warn("{} is outside 0.0 … 1.0, keeping {}", zahl, ersatz);
                return ersatz;
            }
            return zahl;
        } catch (NumberFormatException fehler) {
            LootScaler.LOG.warn("'{}' is not a number, keeping {}", wert, ersatz);
            return ersatz;
        }
    }

    private void schreibe(Path pfad) {
        try {
            Files.createDirectories(pfad.getParent());
            Files.writeString(pfad, VORLAGE.formatted(ores, mobs, neverZero, debug));
            LootScaler.LOG.info("wrote a fresh {}", pfad);
        } catch (IOException fehler) {
            LootScaler.LOG.error("could not write {}: {}", pfad, fehler.getMessage());
        }
    }

    /** Nothing to do at all — used to keep the mixin out of the way when it would change nothing. */
    public boolean untaetig() {
        return ores >= 1.0 && mobs >= 1.0;
    }
}

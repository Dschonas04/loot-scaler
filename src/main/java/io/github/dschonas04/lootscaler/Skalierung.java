package io.github.dschonas04.lootscaler;

import java.util.function.Consumer;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;

/**
 * Turns the multipliers from the config into smaller stacks.
 *
 * <p>The rule differs between the two cases on purpose:
 *
 * <ul>
 *   <li><b>Ores</b> keep their first item, always. Only what comes on top is scaled — the
 *       Fortune bonus, and the ores that give several items at once. Mining a single diamond
 *       therefore always yields a diamond.
 *   <li><b>Mobs</b> have their amounts scaled outright, because those are ranges anyway
 *       (zero to two rotten flesh, one to three beef). With {@code never_zero} a drop of one
 *       still stays one.
 * </ul>
 *
 * <p>Fractions are rounded with the loot context's own random source, so 1.4 items means
 * "one, and a second one four times out of ten" instead of a silently swallowed remainder.
 */
public final class Skalierung {

    private Skalierung() {
    }

    /** Wraps the consumer the loot pool writes into, so every stack passes through here. */
    public static Consumer<ItemStack> huelle(Consumer<ItemStack> ziel, LootContext kontext) {
        Einstellungen werte = LootScaler.einstellungen();
        if (werte.untaetig()) {
            return ziel;
        }
        Art art = artBestimmen(kontext);
        if (art == Art.NICHTS) {
            return ziel;
        }
        double faktor = art == Art.ERZ ? werte.ores : werte.mobs;
        if (faktor >= 1.0) {
            return ziel;
        }
        return stapel -> {
            int vorher = stapel.getCount();
            int nachher = art == Art.ERZ
                    ? nurDenUeberschuss(vorher, faktor, kontext.getRandom())
                    : ganzeMenge(vorher, faktor, werte.neverZero, kontext.getRandom());
            if (nachher <= 0) {
                if (werte.debug) {
                    LootScaler.LOG.info("{} x{} dropped entirely", stapel.getItem(), vorher);
                }
                return;
            }
            if (nachher != vorher) {
                stapel.setCount(nachher);
                if (werte.debug) {
                    LootScaler.LOG.info("{} {} -> {}", stapel.getItem(), vorher, nachher);
                }
            }
            ziel.accept(stapel);
        };
    }

    /** One item is untouchable, the rest is scaled: 1 stays 1, five at 0.7 become four. */
    private static int nurDenUeberschuss(int menge, double faktor, RandomSource zufall) {
        if (menge <= 1) {
            return menge;
        }
        return 1 + runden((menge - 1) * faktor, zufall);
    }

    private static int ganzeMenge(int menge, double faktor, boolean nieNull, RandomSource zufall) {
        int neu = runden(menge * faktor, zufall);
        return nieNull && menge >= 1 ? Math.max(1, neu) : neu;
    }

    /** 1.4 becomes 1 in six cases out of ten and 2 in four. */
    private static int runden(double zahl, RandomSource zufall) {
        int ganz = (int) Math.floor(zahl);
        return zufall.nextDouble() < zahl - ganz ? ganz + 1 : ganz;
    }

    private enum Art {
        ERZ,
        MOB,
        NICHTS
    }

    private static Art artBestimmen(LootContext kontext) {
        BlockState zustand = kontext.getOptionalParameter(LootContextParams.BLOCK_STATE);
        if (zustand != null) {
            return istErz(zustand) ? Art.ERZ : Art.NICHTS;
        }
        if (kontext.getOptionalParameter(LootContextParams.THIS_ENTITY) instanceof LivingEntity wesen
                && !(wesen instanceof Player)) {
            return Art.MOB;
        }
        return Art.NICHTS;
    }

    /**
     * An ore is anything whose id says so, plus the two that do not carry the word: ancient
     * debris and gilded blackstone. That covers modded ores without a hand-kept list.
     */
    private static boolean istErz(BlockState zustand) {
        Identifier name = BuiltInRegistries.BLOCK.getKey(zustand.getBlock());
        String pfad = name.getPath();
        return pfad.contains("ore") || pfad.equals("ancient_debris") || pfad.equals("gilded_blackstone");
    }
}

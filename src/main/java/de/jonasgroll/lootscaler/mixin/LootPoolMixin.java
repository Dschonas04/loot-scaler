package de.jonasgroll.lootscaler.mixin;

import de.jonasgroll.lootscaler.Skalierung;
import java.util.function.Consumer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.LootPool;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

/**
 * Every pool of every loot table hands its items to a consumer. This slips a wrapper in
 * front of that consumer, which is why the mod needs no list of loot tables and works with
 * modded ores and mobs out of the box.
 */
@Mixin(LootPool.class)
public class LootPoolMixin {

    @ModifyVariable(
            method = "addRandomItems(Ljava/util/function/Consumer;Lnet/minecraft/world/level/storage/loot/LootContext;)V",
            at = @At("HEAD"),
            argsOnly = true,
            index = 1)
    private Consumer<ItemStack> lootScalerHuelle(
            Consumer<ItemStack> ziel, Consumer<ItemStack> unbenutzt, LootContext kontext) {
        return Skalierung.huelle(ziel, kontext);
    }
}

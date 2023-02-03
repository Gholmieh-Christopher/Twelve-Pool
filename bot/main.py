# Written by: Christopher Gholmieh
# Imports:

# StarCraft II:
# > Position:
from sc2.position import Point2

# > Bot AI:
from sc2.bot_ai import BotAI, Race

# > Units:
from sc2.units import Units

# > Unit:
from sc2.unit import Unit

# > IDs:
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId

# Typing:
import typing

# Loguru:
import loguru

# Classes:
class TwelvePool(BotAI):
    # Configuration:
    NAME: str = "Twelve Pool"

    RACE: Race = Race.Zerg

    # Events:
    async def on_start(self) -> None:
        pass

    async def on_step(self, iteration: int) -> None:
        zerglings: Units = self.units.of_type(UnitTypeId.ZERGLING)
        queens: Units = self.units.of_type(UnitTypeId.QUEEN)

        if (
            self.can_afford(UnitTypeId.SPAWNINGPOOL)
            and self.structures.of_type(UnitTypeId.SPAWNINGPOOL).amount == 0
            and self.already_pending(UnitTypeId.SPAWNINGPOOL) == 0
        ):
            drone: typing.Optional[Unit] = self.workers.random
            if drone is None:
                loguru.logger.info("No drone available to construct spawning pool.")
                return None

            position: typing.Optional[Point2] = await self.find_placement(UnitTypeId.SPAWNINGPOOL, near=self.townhalls.first.position)
            if position is None:
                loguru.logger.info("No position available to construct spawning pool.")
                return None

            drone.build(UnitTypeId.SPAWNINGPOOL, position)
        
        if self.structures.of_type(UnitTypeId.SPAWNINGPOOL).ready.amount == 1:
            for larva in self.larva:
                if (
                    self.supply_left <= 2
                    and self.already_pending(UnitTypeId.OVERLORD) == 0 
                    and self.can_afford(UnitTypeId.OVERLORD)
                    and self.structures.of_type(UnitTypeId.SPAWNINGPOOL).ready.amount == 1
                ):
                    larva.train(UnitTypeId.OVERLORD)

                    continue

                if self.can_afford(UnitTypeId.ZERGLING) is False:
                    break

                larva.train(UnitTypeId.ZERGLING)
        
        for zergling in zerglings.idle:
            zergling.attack(self.enemy_start_locations[0])

        if (
            self.can_afford(UnitTypeId.QUEEN)
            and self.already_pending(UnitTypeId.QUEEN) == 0
            and self.units.of_type(UnitTypeId.QUEEN).amount == 0
            and self.structures.of_type(UnitTypeId.SPAWNINGPOOL).ready.amount == 1
        ):
            self.townhalls.first.train(UnitTypeId.QUEEN)
        
        if (
            self.minerals >= 500
        ):
            await self.expand_now(UnitTypeId.HATCHERY)

        # TODO: Add speedmining
        # TODO: Queens per individual hatchery
        # TODO: Add a mix of drones.

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
from sc2.ids.buff_id import BuffId

# Typing:
import typing

# Loguru:
import loguru


# Classes:
class TwelvePool(BotAI):
    # Configuration:
    NAME: str = "Twelve Pool"

    RACE: Race = Race.Zerg

    # Methods:
    async def speedmine_single(self, drone: Unit) -> None:
        mineral_field: Unit = self.mineral_field.closest_to(drone)
        if mineral_field is None:
            return None

        townhall: Unit = self.townhalls.closest_to(drone)
        if townhall is None:
            return None

        if drone.is_returning and len(drone.orders) == 1:
            target: Point2 = townhall.position.towards(
                drone, townhall.radius + drone.radius
            )

            if 0.75 < drone.distance_to(target) < 2:
                drone.move(target)
                drone(AbilityId.SMART, townhall, queue=True)

                return None

            if (
                drone.is_returning is False
                and len(drone.orders) == 1
                and isinstance(drone.order_target, int)
            ):
                if 0.75 < drone.distance_to(townhall) < 2:
                    drone.move(townhall)
                    drone(AbilityId.SMART, mineral_field, queue=True)

    # Events:
    async def on_building_construction_complete(self, unit: Unit):
        if unit.type_id == UnitTypeId.HATCHERY:
            mineral_field: typing.Optional[Unit] = self.mineral_field.closest_to(unit)
            if mineral_field is None:
                return None

            unit(AbilityId.RALLY_WORKERS, mineral_field)

    async def on_unit_created(self, unit: Unit) -> None:
        if unit.type_id == UnitTypeId.QUEEN:
            townhall: typing.Optional[Unit] = self.townhalls.closest_to(unit)
            if townhall is None:
                self.idle_queens.add(unit.tag)
            else:
                if townhall.tag in self.queen_registry:
                    self.idle_queens.add(unit.tag)
                else:
                    self.queen_registry[townhall.tag] = unit.tag
                    unit(AbilityId.EFFECT_INJECTLARVA, townhall)

    async def on_unit_destroyed(self, unit_tag: int) -> None:
        if unit_tag not in self.queen_registry:
            return None

        if unit_tag in self.queen_registry.values():
            del self.queen_registry[unit_tag]
            pass

        unready_townhalls: Units = self.townhalls.filter(
            lambda townhall: not townhall.is_ready
        )
        if not any(unready_townhalls):
            self.idle_queens.add(self.queen_registry[unit_tag])
        else:
            self.queen_registry[unit_tag] = unready_townhalls.closest_to(
                self.queen_registry[unit_tag]
            )

        del self.queen_registry[unit_tag]

    async def on_start(self) -> None:
        self.queen_registry: dict = {
            # NOTE: townhall_id: queen_tag
        }

        self.idle_queens: set = set()
        self.idle_clean: set = set()

        self.threshold: int = 15

        self._workers: set = set({UnitTypeId.PROBE, UnitTypeId.DRONE, UnitTypeId.SCV})
        self.drone_streak_max: int = 3

    async def on_step(self, iteration: int) -> None:
        drone_streak: int = 0
        zerglings: Units = self.units.of_type(UnitTypeId.ZERGLING)

        if (
            self.can_afford(UnitTypeId.SPAWNINGPOOL)
            and self.structures.of_type(UnitTypeId.SPAWNINGPOOL).amount == 0
            and self.already_pending(UnitTypeId.SPAWNINGPOOL) == 0
        ):
            drone: typing.Optional[Unit] = self.workers.random
            if drone is None:
                loguru.logger.info("No drone available to construct spawning pool.")
                return None

            position: typing.Optional[Point2] = await self.find_placement(
                UnitTypeId.SPAWNINGPOOL, near=self.townhalls.first.position.towards(self.game_info.map_center, 5)
            )
            if position is None:
                loguru.logger.info("No position available to construct spawning pool.")
                return None

            drone.build(UnitTypeId.SPAWNINGPOOL, position)

        for hatchery in self.townhalls.ready:
            if (
                hatchery.assigned_harvesters < 16
                and zerglings.amount
                >= self.enemy_units.filter(
                    lambda unit: not unit.is_flying
                    and unit.type_id
                    not in self._workers
                ).amount
                * 2 + 8 + (self.townhalls.amount * 2)
                and self.structures.of_type(UnitTypeId.SPAWNINGPOOL).ready.amount == 1
                and self.workers.amount < 80
            ):
                for larva in self.units.of_type(UnitTypeId.LARVA).closer_than(
                    5, hatchery
                ):
                    if self.can_afford(UnitTypeId.DRONE) and drone_streak < self.drone_streak_max:
                        larva.train(UnitTypeId.DRONE)
                        drone_streak += 1

        if self.structures.of_type(UnitTypeId.SPAWNINGPOOL).ready.amount == 1:
            for larva in self.larva:
                if (
                    self.supply_left <= 2
                    and self.already_pending(UnitTypeId.OVERLORD) <= 1
                    and self.can_afford(UnitTypeId.OVERLORD)
                    and self.structures.of_type(UnitTypeId.SPAWNINGPOOL).ready.amount
                    == 1
                ):
                    larva.train(UnitTypeId.OVERLORD)

                    continue

                if self.can_afford(UnitTypeId.ZERGLING) is False:
                    break

                larva.train(UnitTypeId.ZERGLING)

        for zergling in zerglings.idle:
            if (
                self.enemy_structures.filter(
                    lambda structure: structure.type_id == UnitTypeId.ORBITALCOMMAND
                    or structure.type_id == UnitTypeId.PLANETARYFORTRESS
                    or structure.type_id == UnitTypeId.COMMANDCENTER
                    or structure.type_id == UnitTypeId.NEXUS
                    or structure.type_id == UnitTypeId.HATCHERY
                    or structure.type_id == UnitTypeId.LAIR
                    or structure.type_id == UnitTypeId.HIVE
                    or structure.type_id == UnitTypeId.ORBITALCOMMANDFLYING
                    or structure.type_id == UnitTypeId.COMMANDCENTERFLYING
                ).amount
                == 0
            ):
                if self.enemy_structures.amount > 0:
                    zergling.attack(self.enemy_structures.closest_to(zergling).position)

                    continue

            zergling.attack(self.enemy_start_locations[0])

        if self.minerals >= 500:
            await self.expand_now(UnitTypeId.HATCHERY)

        for queen in self.idle_queens:
            available: Units = self.townhalls.filter(
                lambda townhall: townhall.tag not in self.queen_registry
            )
            if not any(available):
                return None
            townhall: Unit = available.closest_to(queen)

            self.queen_registry[townhall.tag] = queen.tag
            if queen.energy >= 25:
                queen(AbilityId.EFFECT_INJECTLARVA, townhall)
            else:
                queen.move(townhall)
            self.idle_clean.add(queen.tag)

        for tag in self.idle_clean:
            self.idle_clean.remove(tag)

        self.idle_clean: set = set()

        for hatchery in self.townhalls:
            if (
                hatchery.tag not in self.queen_registry
                and hatchery.is_idle
                and self.can_afford(UnitTypeId.QUEEN)
                and self.structures.of_type(UnitTypeId.SPAWNINGPOOL).ready.amount == 1
            ):
                hatchery.train(UnitTypeId.QUEEN)

            if hatchery.tag in self.queen_registry:
                queen: Unit = self.units.of_type(UnitTypeId.QUEEN).find_by_tag(
                    self.queen_registry[hatchery.tag]
                )
                if queen.energy >= 25:
                    queen(AbilityId.EFFECT_INJECTLARVA, hatchery)

        for worker in self.workers:
            await self.speedmine_single(worker)

from __future__ import annotations

import uuid
from itertools import count
from unittest.mock import AsyncMock

import pytest

from app.models.meal_plan import MealPlanItem
from app.models.menu_item import MenuItem
from app.services.importer.intents import Persist, Skip
from app.services.importer.items import MenuItemImportItem
from app.services.importer.orchestrator import ImportOrchestrator


class FakeReadContext:
    def __init__(self, existing_items: list | None = None):
        self._items = existing_items or []

    async def find_by_id(self, entity_type, id):
        return next((i for i in self._items if i.id == id), None)

    async def find_by(self, entity_type, **filters):
        return [i for i in self._items if all(getattr(i, k, None) == v for k, v in filters.items())]


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def meal_plan_id():
    return uuid.uuid4()


@pytest.fixture
def rank_counter():
    return count(start=0)


class TestMenuItemImportItem:
    async def test_new_item_creates_menu_item(self, user_id, meal_plan_id, rank_counter):
        ctx = FakeReadContext()
        item = MenuItemImportItem(
            name="Chicken Breast",
            body="500g boneless pack",
            intents_declared=["add_to_meal_plan"],
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            rank_counter=rank_counter,
        )

        intents = await item.resolve_intents(ctx)

        assert len(intents) == 2
        assert isinstance(intents[0], Persist)
        assert isinstance(intents[0].entity, MenuItem)
        assert intents[0].entity.name == "Chicken Breast"
        assert intents[0].entity.body == "500g boneless pack"
        assert intents[0].entity.created_by == user_id
        assert intents[0].entity.updated_by == user_id

        assert isinstance(intents[1], Persist)
        assert isinstance(intents[1].entity, MealPlanItem)
        assert intents[1].entity.meal_plan_id == meal_plan_id
        assert intents[1].entity.menu_item_id == intents[0].entity.id
        assert intents[1].entity.rank == 0

    async def test_new_item_without_meal_plan_intent(self, user_id, meal_plan_id, rank_counter):
        ctx = FakeReadContext()
        item = MenuItemImportItem(
            name="Cooking Oil",
            body="1L refined sunflower oil",
            intents_declared=[],
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            rank_counter=rank_counter,
        )

        intents = await item.resolve_intents(ctx)

        assert len(intents) == 1
        assert isinstance(intents[0], Persist)
        assert isinstance(intents[0].entity, MenuItem)
        assert intents[0].entity.name == "Cooking Oil"

    async def test_existing_item_skips(self, user_id, meal_plan_id, rank_counter):
        existing = MenuItem(
            name="Chicken Breast",
            body="500g boneless pack",
            created_by=user_id,
            updated_by=user_id,
        )
        ctx = FakeReadContext(existing_items=[existing])
        item = MenuItemImportItem(
            name="Chicken Breast",
            body="500g boneless pack",
            intents_declared=["add_to_meal_plan"],
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            rank_counter=rank_counter,
        )

        intents = await item.resolve_intents(ctx)

        assert len(intents) == 1
        assert isinstance(intents[0], Skip)
        assert "already exists" in intents[0].reason

    async def test_rank_counter_increments(self, user_id, meal_plan_id):
        ctx = FakeReadContext()
        counter = count(start=5)

        item1 = MenuItemImportItem(
            name="Item A",
            body="Body A",
            intents_declared=["add_to_meal_plan"],
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            rank_counter=counter,
        )
        item2 = MenuItemImportItem(
            name="Item B",
            body="Body B",
            intents_declared=["add_to_meal_plan"],
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            rank_counter=counter,
        )

        intents1 = await item1.resolve_intents(ctx)
        intents2 = await item2.resolve_intents(ctx)

        assert intents1[1].entity.rank == 5
        assert intents2[1].entity.rank == 6

    async def test_no_meal_plan_id_skips_meal_plan_item(self, user_id, rank_counter):
        ctx = FakeReadContext()
        item = MenuItemImportItem(
            name="Chicken Breast",
            body="500g boneless pack",
            intents_declared=["add_to_meal_plan"],
            user_id=user_id,
            meal_plan_id=None,
            rank_counter=rank_counter,
        )

        intents = await item.resolve_intents(ctx)

        assert len(intents) == 1
        assert isinstance(intents[0], Persist)
        assert isinstance(intents[0].entity, MenuItem)

    async def test_unknown_intents_ignored(self, user_id, meal_plan_id, rank_counter):
        ctx = FakeReadContext()
        item = MenuItemImportItem(
            name="Test Item",
            body="Test body",
            intents_declared=["unknown_future_intent", "add_to_meal_plan"],
            user_id=user_id,
            meal_plan_id=meal_plan_id,
            rank_counter=rank_counter,
        )

        intents = await item.resolve_intents(ctx)

        assert len(intents) == 2
        assert isinstance(intents[1], Persist)
        assert isinstance(intents[1].entity, MealPlanItem)


class TestImportOrchestrator:
    async def test_counts_intents(self):
        session = AsyncMock()
        read_ctx = FakeReadContext()

        orchestrator = ImportOrchestrator(session, read_ctx)

        class FakeSupplier:
            @property
            def supplier(self):
                return "test/supplier"

            async def fetch(self):
                yield MenuItemImportItem(
                    name="New Item",
                    body="Body",
                    intents_declared=["add_to_meal_plan"],
                    user_id=uuid.uuid4(),
                    meal_plan_id=uuid.uuid4(),
                    rank_counter=count(start=0),
                )

        result = await orchestrator.run(FakeSupplier())

        assert result.supplier == "test/supplier"
        assert result.intents_applied["persist"] == 2
        assert result.intents_applied["skip"] == 0

    async def test_skip_counted(self):
        existing_user_id = uuid.uuid4()
        existing = MenuItem(
            name="Existing",
            body="Body",
            created_by=existing_user_id,
            updated_by=existing_user_id,
        )
        session = AsyncMock()
        read_ctx = FakeReadContext(existing_items=[existing])

        orchestrator = ImportOrchestrator(session, read_ctx)

        class FakeSupplier:
            @property
            def supplier(self):
                return "test/supplier"

            async def fetch(self):
                yield MenuItemImportItem(
                    name="Existing",
                    body="Body",
                    intents_declared=["add_to_meal_plan"],
                    user_id=existing_user_id,
                    meal_plan_id=uuid.uuid4(),
                    rank_counter=count(start=0),
                )

        result = await orchestrator.run(FakeSupplier())

        assert result.intents_applied["persist"] == 0
        assert result.intents_applied["skip"] == 1

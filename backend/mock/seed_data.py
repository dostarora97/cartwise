"""
Seed local database with test data for browser E2E testing.

Creates users, menu items, and meal plans so the full pipeline can be tested
without needing to manually set up data through the UI.

Run: CARTWISE_ENV=development uv run python -m mock.seed_data
"""

import asyncio

# Must set env before importing app config
import os
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

os.environ.setdefault("CARTWISE_ENV", "development")

from app.config import settings
from app.models.meal_plan import MealPlan, MealPlanItem
from app.models.menu_item import MenuItem
from app.models.user import User


async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Check if already seeded
        result = await session.execute(select(User).where(User.email == "alice@cartwise.local"))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            print("  To re-seed: delete users alice@cartwise.local and bob@cartwise.local")
            await engine.dispose()
            return

        # --- Users ---
        alice = User(
            email="alice@cartwise.local",
            name="Alice",
            oauth_provider="google",
            oauth_id=f"seed-alice-{uuid.uuid4().hex[:8]}",
            splitwise_user_id=99001,
        )
        bob = User(
            email="bob@cartwise.local",
            name="Bob",
            oauth_provider="google",
            oauth_id=f"seed-bob-{uuid.uuid4().hex[:8]}",
            splitwise_user_id=99002,
        )
        session.add_all([alice, bob])
        await session.flush()
        print(f"Created users: Alice ({alice.id}), Bob ({bob.id})")

        # --- Menu Items ---
        items = [
            MenuItem(
                name="Chicken Biryani",
                body="Fragrant basmati rice with spiced chicken",
                created_by=alice.id,
                updated_by=alice.id,
            ),
            MenuItem(
                name="Raita",
                body="Yogurt with cucumber and mint",
                created_by=alice.id,
                updated_by=alice.id,
            ),
            MenuItem(
                name="Paneer Tikka",
                body="Grilled cottage cheese with spices",
                created_by=bob.id,
                updated_by=bob.id,
            ),
            MenuItem(
                name="Naan",
                body="Tandoori flatbread",
                created_by=bob.id,
                updated_by=bob.id,
            ),
            MenuItem(
                name="Lassi",
                body="Sweet yogurt drink",
                created_by=bob.id,
                updated_by=bob.id,
            ),
        ]
        session.add_all(items)
        await session.flush()
        print(f"Created {len(items)} menu items")

        # --- Meal Plans ---
        # Alice eats: Chicken Biryani, Raita
        alice_plan = MealPlan(user_id=alice.id)
        session.add(alice_plan)
        await session.flush()

        alice_plan_items = [
            MealPlanItem(meal_plan_id=alice_plan.id, menu_item_id=items[0].id),  # Chicken Biryani
            MealPlanItem(meal_plan_id=alice_plan.id, menu_item_id=items[1].id),  # Raita
        ]
        session.add_all(alice_plan_items)

        # Bob eats: Paneer Tikka, Naan, Lassi
        bob_plan = MealPlan(user_id=bob.id)
        session.add(bob_plan)
        await session.flush()

        bob_plan_items = [
            MealPlanItem(meal_plan_id=bob_plan.id, menu_item_id=items[2].id),  # Paneer Tikka
            MealPlanItem(meal_plan_id=bob_plan.id, menu_item_id=items[3].id),  # Naan
            MealPlanItem(meal_plan_id=bob_plan.id, menu_item_id=items[4].id),  # Lassi
        ]
        session.add_all(bob_plan_items)

        await session.commit()
        print("Created meal plans for Alice and Bob")

        # --- Store mock Swiggy token in vault ---
        try:
            import json
            import time

            vault_data = json.dumps(
                {
                    "access_token": "mock-swiggy-token-for-seed",
                    "refresh_token": "mock-refresh-token",
                    "expires_at": int(time.time()) + 86400,
                }
            )
            from app.services.vault import store_secret

            await store_secret(
                session,
                f"swiggy_token:{alice.id}",
                vault_data,
                "Mock Swiggy token for Alice (seeded)",
            )
            alice.swiggy_connected_at = datetime.now(UTC)
            await session.commit()
            print("Stored mock Swiggy token for Alice in vault (connected)")
        except Exception as e:
            print(f"  (skipped vault seeding: {e})")

        print("\n--- Seed complete ---")
        print(f"  Alice: {alice.id} (splitwise_user_id=99001)")
        print(f"  Bob:   {bob.id} (splitwise_user_id=99002)")
        print(f"  Menu items: {', '.join(i.name for i in items)}")
        print("\n  Use dev-login to authenticate as either user:")
        print("    POST /api/v1/auth/dev-login {email: 'alice@cartwise.local', name: 'Alice'}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())

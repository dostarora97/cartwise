from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    pass


# Import all models so Alembic autogenerate can detect them
from app.models.meal_plan import MealPlan as MealPlan  # noqa: E402
from app.models.meal_plan import MealPlanItem as MealPlanItem  # noqa: E402
from app.models.menu_item import MenuItem as MenuItem  # noqa: E402
from app.models.user import User as User  # noqa: E402

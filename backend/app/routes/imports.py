from __future__ import annotations

import itertools
import uuid

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.auth.dependencies import CurrentUser
from app.config import settings
from app.database import SessionDep
from app.models.meal_plan import MealPlan, MealPlanItem
from app.schemas.imports import ImportRequest, ImportResultResponse, SupplierInfo
from app.services.importer import ImportOrchestrator, ReadContext, get_supplier

router = APIRouter(prefix="/imports", tags=["imports"])


@router.get("/suppliers", response_model=list[SupplierInfo])
async def list_suppliers(current_user: CurrentUser):
    return [
        SupplierInfo(id=s["id"], name=s["name"], description=s["description"])
        for s in settings.IMPORT_SUPPLIERS
    ]


@router.post("/", response_model=ImportResultResponse)
async def run_import(body: ImportRequest, session: SessionDep, current_user: CurrentUser):
    plan = await _get_or_create_plan(session, current_user.id)

    max_rank_result = await session.execute(
        select(func.coalesce(func.max(MealPlanItem.rank), -1)).where(
            MealPlanItem.meal_plan_id == plan.id
        )
    )
    max_rank = max_rank_result.scalar_one()

    rank_counter = itertools.count(start=max_rank + 1)

    try:
        supplier = get_supplier(
            supplier_id=body.supplier_id,
            user_id=current_user.id,
            meal_plan_id=plan.id,
            rank_counter=rank_counter,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Supplier not found") from None

    read_ctx = ReadContext(session)
    orchestrator = ImportOrchestrator(session, read_ctx)
    result = await orchestrator.run(supplier)

    return ImportResultResponse(
        supplier_id=result.supplier_id, intents_applied=result.intents_applied
    )


async def _get_or_create_plan(session, user_id: uuid.UUID) -> MealPlan:
    result = await session.execute(select(MealPlan).where(MealPlan.user_id == user_id))
    plan = result.scalar_one_or_none()
    if plan is None:
        plan = MealPlan(user_id=user_id)
        session.add(plan)
        await session.flush()
    return plan

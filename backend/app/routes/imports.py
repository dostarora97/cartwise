from __future__ import annotations

import itertools
import uuid

from fastapi import APIRouter
from sqlalchemy import func, select

from app.auth.dependencies import CurrentUser
from app.database import SessionDep
from app.models.meal_plan import MealPlan, MealPlanItem
from app.schemas.imports import ImportRequest, ImportResultResponse, PreviewResponse
from app.services.importer import (
    ConnectorSupplier,
    ImportOrchestrator,
    ReadContext,
    resolve_supplier_client,
)

router = APIRouter(prefix="/imports", tags=["imports"])


@router.get("/preview", response_model=PreviewResponse)
async def preview_import(supplier_id: str, current_user: CurrentUser):
    client, _ = resolve_supplier_client(supplier_id)
    return await client.preview()


@router.post("/", response_model=ImportResultResponse)
async def run_import(body: ImportRequest, session: SessionDep, current_user: CurrentUser):
    client, _ = resolve_supplier_client(body.supplier_id)

    plan = await _get_or_create_plan(session, current_user.id)

    max_rank_result = await session.execute(
        select(func.coalesce(func.max(MealPlanItem.rank), -1)).where(
            MealPlanItem.meal_plan_id == plan.id
        )
    )
    max_rank = max_rank_result.scalar_one()
    rank_counter = itertools.count(start=max_rank + 1)

    supplier = ConnectorSupplier(
        supplier_id=body.supplier_id,
        client=client,
        user_id=current_user.id,
        meal_plan_id=plan.id,
        rank_counter=rank_counter,
    )
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

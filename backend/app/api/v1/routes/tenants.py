from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.infrastructure.db.models.tenant_model import TenantModel
from app.infrastructure.db.models.user_model import UserModel

router = APIRouter()


class TenantSettingsResponse(BaseModel):
    id: str
    name: str
    slug: str
    custom_prompt: str | None = None


class TenantSettingsUpdate(BaseModel):
    name: str
    custom_prompt: str | None = None


@router.get("", response_model=TenantSettingsResponse)
def get_tenant_settings(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> TenantSettingsResponse:
    tenant: TenantModel | None = (
        db.query(TenantModel)
        .filter(TenantModel.id == current_user.tenant_id)
        .first()
    )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant não encontrado.",
        )

    return TenantSettingsResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        custom_prompt=tenant.custom_prompt,
    )


@router.put("", response_model=TenantSettingsResponse)
def update_tenant_settings(
    payload: TenantSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> TenantSettingsResponse:
    tenant: TenantModel | None = (
        db.query(TenantModel)
        .filter(TenantModel.id == current_user.tenant_id)
        .first()
    )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant não encontrado.",
        )

    tenant.name = payload.name
    tenant.custom_prompt = payload.custom_prompt

    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return TenantSettingsResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        custom_prompt=tenant.custom_prompt,
    )
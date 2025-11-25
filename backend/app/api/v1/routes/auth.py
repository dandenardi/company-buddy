from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.google_oauth import oauth, get_google_user_info
from app.core.config import settings
from app.core.jwt_utils import create_access_token
from app.core.deps import get_current_user
from app.core.security import verify_password, hash_password
from app.infrastructure.db.session import get_db
from app.infrastructure.db.models.user_model import UserModel
from app.infrastructure.db.models.tenant_model import TenantModel
from app.schemas.auth import RegisterRequest, LoginRequest, LoginResponse, MeResponse


auth_router = APIRouter()


def generate_tenant_slug(tenant_name: str, database_session: Session) -> str:
    """
    Gera um slug único para o tenant, evitando colisão no banco.
    Ex.: "Minha Empresa" -> "minha-empresa", "minha-empresa-2", etc.
    """
    base_slug = (
        tenant_name.strip()
        .lower()
        .replace(" ", "-")
    )

    slug = base_slug
    slug_index = 1

    while (
        database_session.query(TenantModel)
        .filter(TenantModel.slug == slug)
        .first()
        is not None
    ):
        slug_index += 1
        slug = f"{base_slug}-{slug_index}"

    return slug


# -------------------------------------------------------------------------
# E-mail/senha - registro
# -------------------------------------------------------------------------
@auth_router.post(
    "/register",
    response_model=LoginResponse,
    summary="Register first user and tenant",
)
def register(
    register_data: RegisterRequest,
    database_session: Session = Depends(get_db),
) -> LoginResponse:
    """
    Cria o primeiro tenant + usuário e já retorna um JWT para o cliente.
    """
    existing_user: UserModel | None = (
        database_session.query(UserModel)
        .filter(UserModel.email == register_data.email)
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    # Gera slug único para o tenant
    tenant_slug: str = generate_tenant_slug(
        tenant_name=register_data.tenant_name,
        database_session=database_session,
    )

    new_tenant = TenantModel(
        name=register_data.tenant_name,
        slug=tenant_slug,
    )
    database_session.add(new_tenant)
    database_session.flush()  # garante new_tenant.id

    new_user = UserModel(
        email=register_data.email,
        hashed_password=hash_password(register_data.password),
        full_name=register_data.full_name,
        tenant_id=new_tenant.id,
    )
    database_session.add(new_user)
    database_session.commit()
    database_session.refresh(new_user)

    # Já retorna token para o usuário ficar logado logo após o cadastro
    token_payload: dict[str, Any] = {
        "sub": str(new_user.id),
        "tenant_id": new_user.tenant_id,
        "email": new_user.email,
    }
    access_token: str = create_access_token(token_payload)

    return LoginResponse(access_token=access_token)


# -------------------------------------------------------------------------
# E-mail/senha - login
# -------------------------------------------------------------------------
@auth_router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
)
def login(
    login_data: LoginRequest,
    database_session: Session = Depends(get_db),
) -> LoginResponse:
    """
    Autentica o usuário por e-mail/senha.
    """
    user: UserModel | None = (
        database_session.query(UserModel)
        .filter(UserModel.email == login_data.email)
        .first()
    )

    if user is None or not verify_password(login_data.password, user.hashed_password):
        # Sempre mesma mensagem para não vazar qual campo falhou
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials.",
        )

    token_payload: dict[str, Any] = {
        "sub": str(user.id),
        "tenant_id": user.tenant_id,
        "email": user.email,
    }

    access_token: str = create_access_token(token_payload)

    return LoginResponse(access_token=access_token)


# -------------------------------------------------------------------------
# Google OAuth - iniciar login
# -------------------------------------------------------------------------
@auth_router.get("/login/google", summary="Login with Google")
async def login_google(request: Request) -> Any:
    """
    Redireciona o usuário para o fluxo de autenticação do Google.
    """
    redirect_uri: str = settings.google_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri)


# -------------------------------------------------------------------------
# Google OAuth - callback
# -------------------------------------------------------------------------
@auth_router.get("/login/google/callback")
async def login_google_callback(
    request: Request,
    database_session: Session = Depends(get_db),
):
    user_info = await get_google_user_info(request)

    email = user_info.get("email")
    full_name = user_info.get("name")

    if not email:
        raise HTTPException(400, "Failed to retrieve user email from Google.")

    user = (
        database_session.query(UserModel)
        .filter(UserModel.email == email)
        .first()
    )

    if not user:
        # New user → create new tenant automatically
        tenant_slug = email.split("@")[0]

        new_tenant = TenantModel(
            name=full_name or tenant_slug,
            slug=tenant_slug,
        )
        database_session.add(new_tenant)
        database_session.flush()

        user = UserModel(
            email=email,
            full_name=full_name,
            tenant_id=new_tenant.id,
            hashed_password=hash_password(secrets.token_hex(16)),
        )
        database_session.add(user)
        database_session.commit()
        database_session.refresh(user)

    # Generate our internal JWT
    token_data = {
        "sub": str(user.id),
        "tenant_id": user.tenant_id,
        "email": user.email,
    }

    jwt_token = create_access_token(token_data)

    
    frontend_callback_url = "http://localhost:3000/callback"
    redirect_url = f"{frontend_callback_url}?token={jwt_token}"

    return RedirectResponse(url=redirect_url, status_code=302)

# -------------------------------------------------------------------------
# Info de Usuário logado
# -------------------------------------------------------------------------
@auth_router.get("/me", response_model=MeResponse, summary="Get current user info")
def get_me(current_user: UserModel = Depends(get_current_user)) -> MeResponse:
    """
    Retorna as informações do usuário autenticado.
    """
    tenant = current_user.tenant

    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        tenant=tenant,
    )

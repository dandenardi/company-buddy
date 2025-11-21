from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.google_oauth import oauth, get_google_user_info


from app.schemas.auth import RegisterRequest, LoginRequest, LoginResponse
from app.core.jwt_utils import create_access_token
from app.core.security import verify_password
from app.core.config import settings

from app.core.jwt_utils import create_access_token
from app.core.security import hash_password
import secrets


from app.schemas.auth import RegisterRequest
from app.core.security import hash_password
from app.infrastructure.db.session import get_db
from app.infrastructure.db.models.user_model import UserModel
from app.infrastructure.db.models.tenant_model import TenantModel

auth_router = APIRouter()


@auth_router.post("/register", summary="Register first user and tenant")
def register(register_data: RegisterRequest, database_session: Session = Depends(get_db)):
    existing_user = (
        database_session.query(UserModel)
        .filter(UserModel.email == register_data.email)
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    tenant_slug = register_data.tenant_name.lower().replace(" ", "-")

    existing_tenant = (
        database_session.query(TenantModel)
        .filter(TenantModel.slug == tenant_slug)
        .first()
    )
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A tenant with this name already exists.",
        )

    new_tenant = TenantModel(
        name=register_data.tenant_name,
        slug=tenant_slug,
    )
    database_session.add(new_tenant)
    database_session.flush()  # ensures new_tenant.id is available

    new_user = UserModel(
        email=register_data.email,
        hashed_password=hash_password(register_data.password),
        full_name=register_data.full_name,
        tenant_id=new_tenant.id,
    )
    database_session.add(new_user)
    database_session.commit()
    database_session.refresh(new_user)

    return {
        "message": "Account successfully created.",
        "tenant_id": new_tenant.id,
        "user_id": new_user.id,
    }


@auth_router.post("/login", response_model=LoginResponse, summary="User login")
def login(login_data: LoginRequest, database_session: Session = Depends(get_db)):
    user = (
        database_session.query(UserModel)
        .filter(UserModel.email == login_data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials.",
        )

    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials.",
        )

    token_payload = {
        "sub": str(user.id),
        "tenant_id": user.tenant_id,
        "email": user.email,
    }

    access_token = create_access_token(token_payload)

    return LoginResponse(access_token=access_token)

@auth_router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = settings.google_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri)

@auth_router.get("/login/google/callback")
async def login_google_callback(
    request: Request,
    database_session: Session = Depends(get_db)
):
    user_info = await get_google_user_info(request)

    email = user_info.get("email")
    full_name = user_info.get("name")

    if not email:
        raise HTTPException(400, "Failed to retrieve user email from Google.")

    # Check if user already exists
    user = (
        database_session.query(UserModel)
        .filter(UserModel.email == email)
        .first()
    )

    if not user:
        # New user → create new tenant automatically
        tenant_slug = email.split("@")[0]

        new_tenant = TenantModel(
            name=full_name,
            slug=tenant_slug
        )
        database_session.add(new_tenant)
        database_session.flush()

        user = UserModel(
            email=email,
            full_name=full_name,
            tenant_id=new_tenant.id,
            hashed_password=hash_password(secrets.token_hex(16))  # random password
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

    # Return JWT (can redirect to frontend later)
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "email": user.email,
        "full_name": user.full_name,
        "tenant_id": user.tenant_id
    }

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    tenant_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TenantInfo(BaseModel):
    id: int
    name: str
    slug: str

    class Config:
        from_attributes = True  # Pydantic v2


class MeResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    tenant: TenantInfo

    class Config:
        from_attributes = True
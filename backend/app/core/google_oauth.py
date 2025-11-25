from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from app.core.config import settings

oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


async def get_google_user_info(request: Request):
    """
    Handles Google OAuth callback exchange: code → tokens → user_info
    """
    token = await oauth.google.authorize_access_token(request)
    
    # Fetch user info from Google's userinfo endpoint
    # This avoids complexity with parsing id_token and handling nonces manually
    user_info = await oauth.google.userinfo(token=token)
    return user_info

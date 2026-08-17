from __future__ import annotations

import os

try:
    from authlib.integrations.flask_client import OAuth
except Exception:
    OAuth = None

oauth = OAuth() if OAuth is not None else None


def configure_google(app):
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if OAuth is None or oauth is None or not client_id or not client_secret:
        return False
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return True


def google_enabled() -> bool:
    return bool(
        OAuth is not None
        and oauth is not None
        and os.environ.get("GOOGLE_CLIENT_ID", "").strip()
        and os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    )

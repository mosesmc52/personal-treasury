from plaid import ApiClient, Configuration
from plaid.api.plaid_api import PlaidApi

from .config import Settings, get_settings


def create_plaid_client(settings: Settings | None = None):
    settings = settings or get_settings()
    missing = [name for name, value in (("PLAID_CLIENT_ID", settings.plaid_client_id), ("PLAID_SECRET", settings.plaid_secret), ("PLAID_ACCESS_TOKENS_JSON", settings.plaid_access_tokens)) if not value]
    if missing:
        raise ValueError("Missing required Plaid configuration: " + ", ".join(missing))
    envs = {"sandbox": "https://sandbox.plaid.com", "production": "https://production.plaid.com", "development": "https://development.plaid.com"}
    if settings.plaid_env not in envs:
        raise ValueError("PLAID_ENV must be sandbox, development, or production")
    configuration = Configuration(host=envs[settings.plaid_env], api_key={"clientId": settings.plaid_client_id, "secret": settings.plaid_secret})
    return PlaidApi(ApiClient(configuration)), settings.plaid_access_tokens

import os
import json
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"
    plaid_access_tokens: dict[str, str] | None = None
    aws_region: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    from_address: str = ""
    to_addresses: tuple[str, ...] = ()
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_paper: bool = True


def get_settings() -> Settings:
    raw_tokens = os.getenv("PLAID_ACCESS_TOKENS_JSON", "")
    try:
        access_tokens = json.loads(raw_tokens) if raw_tokens else {}
    except json.JSONDecodeError as exc:
        raise ValueError("PLAID_ACCESS_TOKENS_JSON must be valid JSON") from exc
    if not isinstance(access_tokens, dict) or not all(isinstance(key, str) and isinstance(value, str) and value for key, value in access_tokens.items()):
        raise ValueError("PLAID_ACCESS_TOKENS_JSON must be a non-empty object mapping names to tokens")
    return Settings(
        plaid_client_id=os.getenv("PLAID_CLIENT_ID", ""),
        plaid_secret=os.getenv("PLAID_SECRET", ""),
        plaid_env=os.getenv("PLAID_ENV", "sandbox"),
        plaid_access_tokens=access_tokens,
        aws_region=os.getenv("AWS_SES_REGION_NAME", ""),
        aws_access_key_id=os.getenv("AWS_SES_ACCESS_KEY_ID", ""),
        aws_secret_access_key=os.getenv("AWS_SES_SECRET_ACCESS_KEY", ""),
        from_address=os.getenv("FROM_ADDRESS", ""),
        to_addresses=tuple(address.strip() for address in os.getenv("TO_ADDRESSES", "").split(",") if address.strip()),
        alpaca_api_key=os.getenv("ALPACA_API_KEY", ""),
        alpaca_secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
        alpaca_paper=os.getenv("ALPACA_PAPER", "true").lower() in {"1", "true", "yes"},
    )

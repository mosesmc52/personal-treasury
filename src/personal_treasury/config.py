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
    report_from_email: str = ""
    report_to_email: str = ""


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
        aws_region=os.getenv("AWS_REGION", ""),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        report_from_email=os.getenv("REPORT_FROM_EMAIL", ""),
        report_to_email=os.getenv("REPORT_TO_EMAIL", ""),
    )

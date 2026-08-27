import logging
from html import escape

from .config import get_settings
from .ses import AmazonSES

logger = logging.getLogger(__name__)


def _html_content(content):
    lines = []
    for line in content.splitlines():
        safe_line = escape(line)
        if line.strip() and line == line.upper():
            lines.append(f"<strong>{safe_line}</strong>")
        else:
            lines.append(safe_line)
    return "<html><body style='font-family: monospace; white-space: pre-wrap;'>" + "\n".join(lines) + "</body></html>"


def send_report(subject: str, content: str, settings=None, ses=None, html=False):
    settings = settings or get_settings()
    if not settings.to_addresses:
        print("Email delivery skipped: TO_ADDRESSES is not configured.")
        return False
    ses = ses or AmazonSES(settings.aws_region, settings.aws_access_key_id, settings.aws_secret_access_key, settings.from_address)
    for address in settings.to_addresses:
        if html:
            ses.send_html_email(address, subject, _html_content(content))
        else:
            ses.send_text_email(address, subject, content)
    logger.info("Email sent successfully")
    return True

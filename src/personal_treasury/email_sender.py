import logging

from .config import get_settings
from .ses import AmazonSES

logger = logging.getLogger(__name__)


def send_report(subject: str, content: str, settings=None, ses=None):
    settings = settings or get_settings()
    if not settings.report_to_email:
        print("Email delivery skipped: REPORT_TO_EMAIL is not configured.")
        return False
    ses = ses or AmazonSES(settings.aws_region, settings.aws_access_key_id, settings.aws_secret_access_key, settings.report_from_email)
    ses.send_text_email(settings.report_to_email, subject, content)
    logger.info("Email sent successfully")
    return True


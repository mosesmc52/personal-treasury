from personal_treasury.config import Settings
from personal_treasury.email_sender import send_report


class FakeSES:
    def __init__(self): self.calls = []
    def send_text_email(self, *args): self.calls.append(args)


def test_ses_receives_recipient_and_subject():
    settings = Settings(report_to_email="to@example.com")
    ses = FakeSES()
    assert send_report("Subject", "Body", settings, ses)
    assert ses.calls == [("to@example.com", "Subject", "Body")]


def test_missing_recipient_skips_email(capsys):
    assert not send_report("Subject", "Body", Settings(), FakeSES())
    assert "Email delivery skipped" in capsys.readouterr().out

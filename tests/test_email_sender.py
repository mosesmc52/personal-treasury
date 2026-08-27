from personal_treasury.config import Settings
from personal_treasury.email_sender import send_report


class FakeSES:
    def __init__(self): self.calls = []
    def send_text_email(self, *args): self.calls.append(args)
    def send_html_email(self, *args): self.calls.append(args)


def test_ses_receives_recipient_and_subject():
    settings = Settings(from_address="from@example.com", to_addresses=("to@example.com", "second@example.com"))
    ses = FakeSES()
    assert send_report("Subject", "Body", settings, ses)
    assert ses.calls == [("to@example.com", "Subject", "Body"), ("second@example.com", "Subject", "Body")]


def test_missing_recipient_skips_email(capsys):
    assert not send_report("Subject", "Body", Settings(), FakeSES())
    assert "TO_ADDRESSES" in capsys.readouterr().out


def test_html_report_bolds_titles():
    settings = Settings(from_address="from@example.com", to_addresses=("to@example.com",))
    ses = FakeSES()
    send_report("Subject", "PERSONAL TREASURY\n\nTotal spending", settings, ses, html=True)
    assert "<strong>PERSONAL TREASURY</strong>" in ses.calls[0][2]

"""Tests for Enron message parsing and sent-mail filtering."""

from __future__ import annotations

from core.email_loader import filter_sent, is_sent_folder, parse_enron_message

_RAW = """Message-ID: <123.456@enron.com>
Date: Mon, 14 May 2001 10:00:00 -0700 (PDT)
From: vince.kaminski@enron.com
To: john@enron.com, jane@enron.com
Subject: Re: model review
X-Folder: \\\\vkaminski\\Sent Mail

Hi team, Thanks for the update. Best, Vince
"""


def test_parse_enron_message():
    msg = parse_enron_message(_RAW)
    assert msg.sender == "vince.kaminski@enron.com"
    assert "john@enron.com" in msg.recipients and len(msg.recipients) == 2
    assert msg.subject == "Re: model review"
    assert "Sent Mail" in msg.folder
    assert msg.body.startswith("Hi team")
    assert msg.timestamp is not None


def test_is_sent_folder():
    assert is_sent_folder("\\\\vkaminski\\Sent Mail")
    assert is_sent_folder("_sent_mail")
    assert not is_sent_folder("\\\\vkaminski\\Inbox")


def test_filter_sent(sample_emails):
    kept = filter_sent(sample_emails, employee="vince.kaminski")
    assert len(kept) == 2
    # an inbox email or wrong sender is dropped
    sample_emails[0].folder = "Inbox"
    assert len(filter_sent(sample_emails, employee="vince.kaminski")) == 1

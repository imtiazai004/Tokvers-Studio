"""
Pluggable email sender. Default `console` provider just logs the message — so
password-reset / verification flows work end-to-end TODAY without any SMTP
account. Set `email_provider=smtp` + SMTP_* env later to actually deliver.
"""
from __future__ import annotations

import abc
import asyncio
import smtplib
from email.message import EmailMessage

import httpx

from .config import settings


class EmailSender(abc.ABC):
    @abc.abstractmethod
    async def send(self, to: str, subject: str, text: str, html: str | None = None) -> None:
        ...


class ConsoleEmailSender(EmailSender):
    """Dev/default: prints the email (incl. any action link) to the server log."""
    async def send(self, to, subject, text, html=None):
        print("\n" + "=" * 60)
        print(f"[EMAIL to {to}] {subject}")
        print("-" * 60)
        print(text)
        print("=" * 60 + "\n", flush=True)


class SmtpEmailSender(EmailSender):
    """Real delivery via SMTP (blocking smtplib run off the event loop)."""
    async def send(self, to, subject, text, html=None):
        msg = EmailMessage()
        msg["From"] = settings.email_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")
        await asyncio.to_thread(self._deliver, msg)

    def _deliver(self, msg: EmailMessage):
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
            s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)


class ResendEmailSender(EmailSender):
    """Real delivery via the Resend HTTP API (https://resend.com). Set
    email_provider=resend, RESEND_API_KEY, and an email_from on a verified
    domain. Errors are logged, not raised, so auth flows never 500 on a mail hiccup."""
    _URL = "https://api.resend.com/emails"

    async def send(self, to, subject, text, html=None):
        if not settings.resend_api_key:
            print("WARNING: email_provider=resend but RESEND_API_KEY is unset; email not sent.", flush=True)
            return
        payload = {"from": settings.email_from, "to": [to], "subject": subject, "text": text}
        if html:
            payload["html"] = html
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    self._URL,
                    headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                    json=payload,
                )
            if resp.status_code >= 300:
                print(f"WARNING: Resend send failed ({resp.status_code}): {resp.text[:300]}", flush=True)
        except Exception as e:
            print(f"WARNING: Resend send error: {e}", flush=True)


_SENDERS: dict[str, EmailSender] = {
    "console": ConsoleEmailSender(),
    "smtp": SmtpEmailSender(),
    "resend": ResendEmailSender(),
}


def get_email_sender() -> EmailSender:
    return _SENDERS.get(settings.email_provider, _SENDERS["console"])


async def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    await get_email_sender().send(to, subject, text, html)

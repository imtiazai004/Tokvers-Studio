"""Signup email policy: format validation + disposable/temp-mail blocklist.

Dependency-free (a solid regex, not a full RFC parser) so it works in prod with
no extra install. The disposable list is a curated set of the most common
throwaway providers — it won't catch every temp-mail domain, but it kills the
casual "temp email + fresh signup" abuse loop, which is the point. It layers
under real email verification, not instead of it. See [[security-hardening-plan]].
"""
import re

# Good-enough email shape: one @, a dot in the domain, no whitespace, bounded length.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Common disposable / temporary email domains (and their many aliases).
DISPOSABLE_DOMAINS: frozenset[str] = frozenset({
    "0-mail.com", "10minutemail.com", "10minutemail.net", "20minutemail.com",
    "33mail.com", "mailinator.com", "mailinator.net", "mailinator2.com",
    "guerrillamail.com", "guerrillamail.net", "guerrillamail.org", "guerrillamail.biz",
    "guerrillamail.de", "grr.la", "sharklasers.com", "spam4.me", "pokemail.net",
    "tempmail.com", "temp-mail.org", "temp-mail.io", "tempmail.net", "tempmailo.com",
    "tempr.email", "tempmailaddress.com", "tmpmail.org", "tmpmail.net", "tmail.ws",
    "throwawaymail.com", "throwaway.email", "getnada.com", "nada.email", "getairmail.com",
    "yopmail.com", "yopmail.net", "yopmail.fr", "cool.fr.nf", "jetable.fr.nf",
    "trashmail.com", "trashmail.net", "trashmail.de", "trash-mail.com", "wegwerfmail.de",
    "mytemp.email", "mohmal.com", "moakt.com", "disposablemail.com", "emailondeck.com",
    "fakemail.net", "fakeinbox.com", "fake-mail.net", "maildrop.cc", "mailnesia.com",
    "mailcatch.com", "mailnull.com", "spamgourmet.com", "dispostable.com", "mintemail.com",
    "mailexpire.com", "spambox.us", "incognitomail.com", "anonbox.net", "mailtemp.net",
    "burnermail.io", "33mail.io", "inboxbear.com", "tempinbox.com", "temp-inbox.com",
    "1secmail.com", "1secmail.net", "1secmail.org", "kzccv.com", "wwjmp.com", "esiix.com",
    "vjuum.com", "laafd.com", "txcct.com", "27email.com", "mailpoof.com", "mailsac.com",
    "harakirimail.com", "spam.la", "byom.de", "discard.email", "discardmail.com",
    "einrot.com", "fleckmail.de", "hidemail.de", "koszmail.pl", "kurzepost.de",
    "objectmail.com", "proxymail.eu", "rcpt.at", "safetymail.info", "sofimail.com",
    "squizzy.de", "tempemail.net", "tempemail.co.za", "trbvm.com", "wilemail.com",
    "yepmail.net", "zoemail.net", "mailedu.de", "mvrht.com", "spamavert.com",
})


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_format(email: str) -> bool:
    return bool(email) and len(email) <= 254 and bool(_EMAIL_RE.match(email))


def is_disposable(email: str) -> bool:
    domain = email.rsplit("@", 1)[-1] if "@" in email else ""
    return domain in DISPOSABLE_DOMAINS

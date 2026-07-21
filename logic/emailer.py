"""
emailer.py
----------
Minimal, optional email sending for password reset links.

Free-tier reality: sending real email needs an SMTP account somewhere.
Gmail's free SMTP (with an "App Password", not your normal password) works
fine for the low volume a personal/small-group app generates — see
DOCUMENTATION.md "Turning on real password-reset emails" for the 5-minute
setup.

Until you configure SMTP env vars (SMTP_HOST, SMTP_PORT, SMTP_USER,
SMTP_PASSWORD), `send_reset_email()` doesn't fail — it just returns the
reset link instead of emailing it, and the route shows it directly on the
page. That keeps the app fully usable at zero setup, with real email as an
opt-in upgrade.
"""

import os
import smtplib
from email.mime.text import MIMEText


def smtp_configured():
    return all(os.environ.get(k) for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD"))


def send_reset_email(to_email, reset_url, lang="en"):
    """Returns True if an email was actually sent, False if SMTP isn't
    configured (caller should then display the link directly instead)."""
    if not smtp_configured():
        return False

    subject = "Reset your Exodus password" if lang == "en" else "Resetează parola Exodus"
    body_en = f"Click this link to reset your Exodus password:\n\n{reset_url}\n\nIf you didn't request this, ignore this email."
    body_ro = f"Apasă acest link pentru a-ți reseta parola Exodus:\n\n{reset_url}\n\nDacă nu ai cerut asta, ignoră acest email."
    body = body_ro if lang == "ro" else body_en

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = to_email

    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ["SMTP_PORT"])) as server:
        server.starttls()
        server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        server.sendmail(os.environ["SMTP_USER"], [to_email], msg.as_string())
    return True

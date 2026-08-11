import os
import smtplib
from email.mime.text import MIMEText


def send(record, subject, body, dry_run=False):
    """Real outbound action. For the prototype every send lands in our own
    throwaway inbox (standing in for the clinician's) with the intended
    recipient banner on top -- swap the single 'To' address for real per-clinician
    delivery and nothing else about this function needs to change."""
    address = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    banner = (
        f"[SIMULATED SEND] Would go to: {record.get('name')} "
        f"<{record.get('email')}> ({record.get('mobile')})\n\n"
    )
    full_body = banner + body
    full_subject = f"[SIM] {subject}"

    if dry_run:
        return {"status": "dry_run", "subject": full_subject}

    msg = MIMEText(full_body)
    msg["Subject"] = full_subject
    msg["From"] = address
    msg["To"] = address

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(address, password)
        server.sendmail(address, [address], msg.as_string())

    return {"status": "sent", "subject": full_subject}

"""
邮件推送 notifier，使用标准库 smtplib。
"""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..models import Alert
from .base import BaseNotifier


class EmailNotifier(BaseNotifier):
    def _send(self, alert: Alert, message: str) -> bool:
        cfg = self.cfg
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "【机票提醒】" + message.splitlines()[0].replace("【机票提醒】", "")
        msg["From"] = cfg["username"]
        msg["To"] = cfg["to"]

        html = "<pre style='font-family:sans-serif;font-size:15px'>" + message + "</pre>"
        msg.attach(MIMEText(message, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["username"], cfg["password"])
            server.sendmail(cfg["username"], cfg["to"], msg.as_string())
        return True

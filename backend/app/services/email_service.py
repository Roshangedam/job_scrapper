"""Email service — sends alert emails with job matches using HTML templates."""

import logging
from typing import List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from jinja2 import Template

from app.config import settings

logger = logging.getLogger(__name__)

# ── HTML Email Template ──
JOB_ALERT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: 'Segoe UI', sans-serif; background: #f4f6f9; margin: 0; padding: 20px; }
    .container { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
    .header { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 24px; text-align: center; }
    .header h1 { margin: 0; font-size: 22px; font-weight: 600; }
    .header p { margin: 8px 0 0; opacity: 0.9; font-size: 14px; }
    .job-card { padding: 20px; border-bottom: 1px solid #eee; }
    .job-title { font-size: 16px; font-weight: 600; color: #1a1a2e; margin: 0 0 4px; }
    .job-company { color: #666; font-size: 14px; margin: 0 0 8px; }
    .match-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
    .match-high { background: #d4edda; color: #155724; }
    .match-mid { background: #fff3cd; color: #856404; }
    .match-low { background: #f8d7da; color: #721c24; }
    .job-meta { font-size: 13px; color: #888; margin-top: 8px; }
    .apply-btn { display: inline-block; padding: 8px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 6px; font-size: 13px; margin-top: 8px; }
    .footer { padding: 16px; text-align: center; color: #999; font-size: 12px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🔍 New Job Matches Found!</h1>
      <p>Engine: {{ engine_name }} | {{ job_count }} new jobs</p>
    </div>
    {% for job in jobs %}
    <div class="job-card">
      <div class="job-title">{{ job.title }}</div>
      <div class="job-company">{{ job.company_name }} · {{ job.location_city }}</div>
      {% if job.match_pct %}
      <span class="match-badge {% if job.match_pct >= 75 %}match-high{% elif job.match_pct >= 50 %}match-mid{% else %}match-low{% endif %}">
        {{ job.match_pct }}% Match
      </span>
      {% endif %}
      <div class="job-meta">
        {% if job.experience_text %}Exp: {{ job.experience_text }} · {% endif %}
        {% if job.salary_text %}{{ job.salary_text }} · {% endif %}
        {{ job.source_platform | upper }}
      </div>
      {% if job.source_url %}
      <a href="{{ job.source_url }}" class="apply-btn">View & Apply →</a>
      {% endif %}
    </div>
    {% endfor %}
    <div class="footer">
      Sent by Job Scrapper Dashboard | {{ timestamp }}
    </div>
  </div>
</body>
</html>
"""


class EmailService:
    """Sends email alerts using SMTP."""

    async def send_job_alert(
        self,
        to_email: str,
        engine_name: str,
        jobs: list,
        smtp_config: dict = None,
    ) -> bool:
        """Send a job alert email with matched jobs."""
        if not jobs:
            return False

        config = smtp_config or {
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "email": settings.SMTP_EMAIL,
            "password": settings.SMTP_PASSWORD,
            "use_tls": settings.SMTP_USE_TLS,
        }

        if not config.get("host") or not config.get("email"):
            logger.warning("Email not configured — skipping alert")
            return False

        try:
            # Render template
            template = Template(JOB_ALERT_TEMPLATE)
            html = template.render(
                engine_name=engine_name,
                job_count=len(jobs),
                jobs=jobs,
                timestamp=__import__("datetime").datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            )

            # Build email
            msg = MIMEMultipart("alternative")
            msg["From"] = config["email"]
            msg["To"] = to_email
            msg["Subject"] = f"🔍 {len(jobs)} New Job Matches — {engine_name}"
            msg.attach(MIMEText(html, "html"))

            # Send
            await aiosmtplib.send(
                msg,
                hostname=config["host"],
                port=config["port"],
                username=config["email"],
                password=config["password"],
                start_tls=config.get("use_tls", True),
            )

            logger.info(f"📧 Alert email sent to {to_email} ({len(jobs)} jobs)")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False

    async def test_connection(self, smtp_config: dict) -> dict:
        """Test SMTP connection."""
        try:
            smtp = aiosmtplib.SMTP(
                hostname=smtp_config["host"],
                port=smtp_config["port"],
                start_tls=smtp_config.get("use_tls", True),
            )
            await smtp.connect()
            await smtp.login(smtp_config["email"], smtp_config["password"])
            await smtp.quit()
            return {"success": True, "message": "Connection successful"}
        except Exception as e:
            return {"success": False, "message": str(e)}


# Singleton
email_service = EmailService()

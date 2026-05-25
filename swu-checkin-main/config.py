import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-to-a-random-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email config (SMTP)
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.qq.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "")

    # Auto check-in schedule (Beijing time)
    CHECKIN_HOUR = 21
    CHECKIN_MINUTE = 10

    # Manual check-in available time window
    MANUAL_START_HOUR = 21
    MANUAL_END_HOUR = 23
    MANUAL_END_MINUTE = 30

    # New user default check-in credits
    DEFAULT_CREDITS = 3

    # Purchase package
    PACKAGE_PRICE = 3  # yuan
    PACKAGE_COUNT = 30  # check-in times

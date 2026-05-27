import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-to-a-random-secret-key")
    # Separate key for password encryption — changing SECRET_KEY won't break logins
    PASSWORD_ENCRYPTION_KEY = os.environ.get("PASSWORD_ENCRYPTION_KEY", "change-me-to-a-r")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Resend email API key (https://resend.com)
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "re_eYfVMpAr_BpNJrd6NGi42GPu2hyoWt2T3")

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

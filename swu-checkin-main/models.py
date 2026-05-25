from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

# Beijing timezone offset
CHINA_OFFSET = timedelta(hours=8)


def china_now():
    """Return current Beijing time as naive datetime (for SQLite compatibility)."""
    return (datetime.now(timezone.utc) + CHINA_OFFSET).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    campus_password = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    credits = db.Column(db.Integer, default=0, nullable=False)
    auto_checkin = db.Column(db.Boolean, default=False, nullable=False)
    terms_accepted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=china_now)
    updated_at = db.Column(db.DateTime, default=china_now, onupdate=china_now)
    deleted_at = db.Column(db.DateTime, nullable=True)

    checkin_logs = db.relationship("CheckinLog", backref="user", lazy="dynamic",
                                   order_by="CheckinLog.created_at.desc()")
    orders = db.relationship("Order", backref="user", lazy="dynamic",
                             order_by="Order.created_at.desc()")


class EmailCode(db.Model):
    __tablename__ = "email_codes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(128), nullable=False, index=True)
    code = db.Column(db.String(32), nullable=False)
    purpose = db.Column(db.String(32), default="register")
    used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=china_now)


class DeletedUserRecord(db.Model):
    """Record of deleted users for credit recovery on re-registration."""
    __tablename__ = "deleted_user_records"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), nullable=False)
    remaining_credits = db.Column(db.Integer, default=0)
    deleted_at = db.Column(db.DateTime, default=china_now)


class CheckinLog(db.Model):
    __tablename__ = "checkin_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(32), nullable=False)
    message = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=china_now)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    order_no = db.Column(db.String(64), unique=True, nullable=False)
    amount = db.Column(db.Integer, default=0)
    credits = db.Column(db.Integer, default=0)
    status = db.Column(db.String(32), default="pending")
    created_at = db.Column(db.DateTime, default=china_now)
    paid_at = db.Column(db.DateTime, nullable=True)


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text, nullable=False)
    page = db.Column(db.String(64), default="home")
    target_user_id = db.Column(db.Integer, nullable=True)  # None = global, otherwise user-specific
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=china_now)


class SiteSetting(db.Model):
    """Key-value settings editable from admin panel."""
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, default="")
    description = db.Column(db.String(256), default="")
    updated_at = db.Column(db.DateTime, default=china_now, onupdate=china_now)


def get_setting(key, default=None):
    """Get a site setting value by key."""
    s = SiteSetting.query.filter_by(key=key).first()
    return s.value if s else default


def set_setting(key, value, description=""):
    """Set a site setting value."""
    s = SiteSetting.query.filter_by(key=key).first()
    if not s:
        s = SiteSetting(key=key, description=description)
        db.session.add(s)
    s.value = str(value)
    s.description = description
    db.session.commit()
    return s

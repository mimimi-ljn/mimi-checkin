import os
import sys
import uuid
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from config import Config
from models import db, User, EmailCode, DeletedUserRecord, CheckinLog, Order, Announcement, SiteSetting, get_setting, set_setting, china_now

CHINA_TZ = timezone(timedelta(hours=8))

login_manager = LoginManager()

# Add scripts to path
_SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)


def _get_encryption_key():
    """Get password encryption key from config (independent of SECRET_KEY)."""
    try:
        return app.config["PASSWORD_ENCRYPTION_KEY"][:16]
    except (RuntimeError, KeyError):
        return "change-me-to-a-r"


def _simple_encrypt(password, key=None):
    if key is None:
        key = _get_encryption_key()
    result = []
    for i, c in enumerate(password):
        kc = ord(key[i % len(key)])
        result.append(chr(ord(c) ^ kc))
    return base64.urlsafe_b64encode("".join(result).encode()).decode()


def _simple_decrypt(encrypted, key=None):
    if key is None:
        key = _get_encryption_key()
    data = base64.urlsafe_b64decode(encrypted.encode()).decode()
    result = []
    for i, c in enumerate(data):
        kc = ord(key[i % len(key)])
        result.append(chr(ord(c) ^ kc))
    return "".join(result)


def encrypt_password(password):
    try:
        from cryptography.fernet import Fernet
        key = _get_encryption_key().encode()
        f = Fernet(base64.urlsafe_b64encode(key.ljust(32, b"0")[:32]))
        return f.encrypt(password.encode()).decode()
    except (ImportError, Exception):
        return _simple_encrypt(password)


def decrypt_password(encrypted):
    try:
        from cryptography.fernet import Fernet
        key = _get_encryption_key().encode()
        f = Fernet(base64.urlsafe_b64encode(key.ljust(32, b"0")[:32]))
        return f.decrypt(encrypted.encode()).decode()
    except (ImportError, Exception):
        return _simple_decrypt(encrypted)


def hash_email(email):
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


def is_manual_checkin_time():
    now = china_now()
    hour = now.hour
    minute = now.minute
    if hour < 21 or hour > 23:
        return False
    if hour == 23 and minute > 30:
        return False
    return True


def _init_default_settings():
    defaults = {
        "payment_enabled": "true",
        "registration_enabled": "true",
        "manual_checkin_enabled": "true",
        "site_title": "签到系统",
        "pricing_text": "3 元 / 30 次",
        "package_price": "3",
        "package_count": "30",
        "new_user_credits": "3",
        "home_notice": "",
    }
    for k, v in defaults.items():
        if not SiteSetting.query.filter_by(key=k).first():
            db.session.add(SiteSetting(key=k, value=v, description=""))
    db.session.commit()


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.id != 1:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def get_all_settings():
    settings = {}
    for s in SiteSetting.query.all():
        settings[s.key] = s.value
    return settings


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login_page"
    login_manager.login_message = None

    with app.app_context():
        db.create_all()
        _migrate_db()
        _init_default_settings()

    return app


def _migrate_db():
    """Add missing columns to existing tables (safe to call on every startup)."""
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    # Add target_user_id to announcements if missing
    cols = [c["name"] for c in inspector.get_columns("announcements")]
    if "target_user_id" not in cols:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE announcements ADD COLUMN target_user_id INTEGER"))
            conn.commit()


app = create_app()


@app.after_request
def add_cache_headers(response):
    """Prevent Cloudflare and browsers from caching HTML that may contain
    user-specific data (e.g. navbar showing logged-in username)."""
    response.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Inject settings into all templates
@app.context_processor
def inject_settings():
    return {"site_settings": get_all_settings()}


# ─── Page Routes ──────────────────────────────────────────────────────────────

@app.route("/")
def home_page():
    return render_template("home.html")


@app.route("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_page"))
    return render_template("login.html")


@app.route("/register")
def register_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_page"))
    return render_template("register.html")


@app.route("/terms")
def terms_page():
    return render_template("terms.html")


@app.route("/forgot-password")
def forgot_password_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_page"))
    return render_template("forgot_password.html")


@app.route("/dashboard")
@login_required
def dashboard_page():
    if current_user.deleted_at:
        logout_user()
        return redirect(url_for("login_page"))
    return render_template("dashboard.html")


# ─── Auth API ─────────────────────────────────────────────────────────────────

@app.route("/api/v1/auth/register", methods=["POST"])
def api_register():
    if get_setting("registration_enabled", "true") != "true":
        return jsonify({"detail": "注册功能暂未开放"}), 400
    data = request.get_json() or {}
    invite_code = (data.get("invite_code") or "").strip()
    username = (data.get("username") or "").strip()
    campus_password = (data.get("campus_password") or "")
    email = (data.get("email") or "").strip().lower()
    email_code = (data.get("email_code") or "").strip()

    errors = []
    if invite_code != "MImi":
        errors.append("内测码错误")
    if not username:
        errors.append("请输入校园网账号")
    if not campus_password:
        errors.append("请输入密码")
    if not email:
        errors.append("请输入邮箱地址")
    if not email_code:
        errors.append("请输入验证码")

    if errors:
        return jsonify({"detail": "；".join(errors)}), 422

    # Verify email code
    code_record = (
        EmailCode.query
        .filter_by(email=email, code=email_code, purpose="register", used=False)
        .order_by(EmailCode.created_at.desc())
        .first()
    )
    if not code_record or code_record.expires_at < china_now():
        return jsonify({"detail": "验证码错误或已过期"}), 422

    # Check if username already exists (active)
    existing = User.query.filter_by(username=username, deleted_at=None).first()
    if existing:
        return jsonify({"detail": "该校园网账号已被注册"}), 409

    # Check if email already registered (active)
    existing_email = User.query.filter_by(email=email, deleted_at=None).first()
    if existing_email:
        return jsonify({"detail": "该邮箱已被注册"}), 409

    # Restore credits from a previously deleted account
    restored = DeletedUserRecord.query.filter_by(username=username).order_by(
        DeletedUserRecord.deleted_at.desc()
    ).first()
    default_credits = int(get_setting("new_user_credits", str(Config.DEFAULT_CREDITS)))
    initial_credits = restored.remaining_credits if restored else default_credits

    user = User(
        username=username,
        campus_password=encrypt_password(campus_password),
        email=email,
        credits=initial_credits,
        terms_accepted=True,
    )
    db.session.add(user)
    code_record.used = True
    db.session.commit()

    login_user(user, remember=True)
    return jsonify({"message": "注册成功", "user_id": user.id}), 201


@app.route("/api/v1/auth/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    campus_password = (data.get("campus_password") or "")

    if not username or not campus_password:
        return jsonify({"detail": "请输入校园网账号和密码"}), 422

    user = User.query.filter_by(username=username, deleted_at=None).first()
    if not user:
        return jsonify({"detail": "账号或密码错误"}), 401

    try:
        stored_pw = decrypt_password(user.campus_password)
    except Exception:
        stored_pw = user.campus_password

    if stored_pw != campus_password:
        return jsonify({"detail": "账号或密码错误"}), 401

    login_user(user, remember=True)
    return jsonify({"message": "登录成功", "user_id": user.id})


@app.route("/api/v1/auth/logout", methods=["POST"])
def api_logout():
    logout_user()
    return jsonify({"message": "已退出登录"})


@app.route("/api/v1/auth/reset-password", methods=["POST"])
def api_reset_password():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    email_code = (data.get("email_code") or "").strip()
    new_password = (data.get("campus_password") or "")

    if not username or not email or not email_code or not new_password:
        return jsonify({"detail": "请填写所有字段"}), 422

    code_record = (
        EmailCode.query
        .filter_by(email=email, code=email_code, purpose="reset_password", used=False)
        .order_by(EmailCode.created_at.desc())
        .first()
    )
    if not code_record or code_record.expires_at < china_now():
        return jsonify({"detail": "验证码错误或已过期"}), 422

    user = User.query.filter_by(username=username, email=email, deleted_at=None).first()
    if not user:
        return jsonify({"detail": "账号或邮箱不匹配"}), 404

    user.campus_password = encrypt_password(new_password)
    code_record.used = True
    db.session.commit()

    return jsonify({"message": "密码重置成功"})


@app.route("/api/v1/auth/send-code", methods=["POST"])
def api_send_code():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    purpose = (data.get("purpose") or "register").strip()

    # For "delete" purpose with logged-in user, use their email
    if not email and purpose == "delete" and current_user.is_authenticated:
        email = current_user.email

    if not email:
        return jsonify({"detail": "请输入邮箱地址"}), 422

    # Rate limit: check last code sent within 60 seconds
    recent = (
        EmailCode.query
        .filter_by(email=email, purpose=purpose)
        .order_by(EmailCode.created_at.desc())
        .first()
    )
    if recent and (china_now() - recent.created_at).total_seconds() < 60:
        return jsonify({"detail": "发送过于频繁，请 60 秒后再试"}), 429

    from services.email_service import generate_code, send_email

    code = generate_code()
    email_config = {
        "RESEND_API_KEY": app.config.get("RESEND_API_KEY", ""),
    }

    success, error = send_email(email_config, email, code)

    # Always save the code (in dev mode, printed to console)
    code_record = EmailCode(
        email=email,
        code=code,
        purpose=purpose,
        expires_at=china_now() + timedelta(minutes=10),
    )
    db.session.add(code_record)
    db.session.commit()

    if not success:
        return jsonify({"detail": error or "验证码发送失败"}), 500

    return jsonify({"message": "验证码已发送"})


# ─── User API ─────────────────────────────────────────────────────────────────

@app.route("/api/v1/users/me", methods=["GET"])
@login_required
def api_get_me():
    user = current_user
    if user.deleted_at:
        logout_user()
        return jsonify({"detail": "账号已删除"}), 401

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "credits": user.credits,
        "auto_checkin": user.auto_checkin,
        "terms_accepted": user.terms_accepted,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    })


@app.route("/api/v1/users/me", methods=["PUT"])
@login_required
def api_update_me():
    data = request.get_json() or {}
    user = current_user
    if user.deleted_at:
        return jsonify({"detail": "账号已删除"}), 401

    if "campus_password" in data and data["campus_password"]:
        user.campus_password = encrypt_password(data["campus_password"])
    if "email" in data and data["email"]:
        user.email = data["email"].strip().lower()

    db.session.commit()
    return jsonify({"message": "更新成功"})


@app.route("/api/v1/users/me/terms", methods=["POST"])
@login_required
def api_accept_terms():
    user = current_user
    user.terms_accepted = True
    db.session.commit()
    return jsonify({"message": "已同意用户协议"})


@app.route("/api/v1/users/me", methods=["DELETE"])
@login_required
def api_delete_me():
    user = current_user
    email_code = (request.get_json() or {}).get("email_code", "").strip()

    if not email_code:
        return jsonify({"detail": "请输入邮箱验证码"}), 422

    code_record = (
        EmailCode.query
        .filter_by(email=user.email, code=email_code, purpose="delete", used=False)
        .order_by(EmailCode.created_at.desc())
        .first()
    )
    if not code_record or code_record.expires_at < china_now():
        return jsonify({"detail": "验证码错误或已过期"}), 422

    # Record credits for potential recovery
    record = DeletedUserRecord(username=user.username, remaining_credits=user.credits)
    db.session.add(record)
    code_record.used = True
    user.deleted_at = china_now()
    db.session.commit()

    logout_user()
    return jsonify({"message": "账号已删除"})


# ─── Check-in API ─────────────────────────────────────────────────────────────

@app.route("/api/v1/checkin/manual", methods=["POST"])
@login_required
def api_manual_checkin():
    if get_setting("manual_checkin_enabled", "true") != "true":
        return jsonify({"detail": "手动签到功能暂未开放"}), 400
    user = current_user
    if user.deleted_at:
        return jsonify({"detail": "账号已删除"}), 401

    # Check time window
    if not is_manual_checkin_time():
        return jsonify({"detail": "手动签到仅在每天 21:00-23:30 可用"}), 400

    # Check if registered less than 3 minutes ago
    if (china_now() - user.created_at).total_seconds() < 180:
        return jsonify({"detail": "注册后 3 分钟内不可手动签到"}), 400

    # Check credits
    if user.credits <= 0:
        return jsonify({"detail": "剩余签到次数不足，请购买签到次数"}), 400

    # Run check-in synchronously
    try:
        campus_pw = decrypt_password(user.campus_password)
    except Exception:
        campus_pw = user.campus_password

    from services.checkin_service import run_checkin
    result_code, status_key, message = run_checkin(user.username, campus_pw)

    # Log the result
    log = CheckinLog(user_id=user.id, status=status_key, message=message)
    db.session.add(log)

    # Only deduct credits on actual success
    if status_key == "success":
        user.credits = max(0, user.credits - 1)

    db.session.commit()

    return jsonify({
        "result_code": result_code,
        "status": status_key,
        "message": message,
        "remaining_credits": user.credits,
    })


@app.route("/api/v1/checkin/auto", methods=["POST"])
@login_required
def api_toggle_auto():
    user = current_user
    if user.deleted_at:
        return jsonify({"detail": "账号已删除"}), 401

    enable = (request.get_json() or {}).get("enable", True)
    user.auto_checkin = enable
    db.session.commit()

    return jsonify({
        "message": "已开启自动签到" if enable else "已关闭自动签到",
        "auto_checkin": user.auto_checkin,
    })


@app.route("/api/v1/checkin/logs", methods=["GET"])
@login_required
def api_checkin_logs():
    user = current_user
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    logs = (
        CheckinLog.query
        .filter_by(user_id=user.id)
        .order_by(CheckinLog.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        "items": [
            {
                "id": log.id,
                "status": log.status,
                "message": log.message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs.items
        ],
        "total": logs.total,
        "page": logs.page,
        "pages": logs.pages,
    })


@app.route("/api/v1/checkin/status", methods=["GET"])
@login_required
def api_checkin_status():
    user = current_user
    latest = CheckinLog.query.filter_by(user_id=user.id).order_by(
        CheckinLog.created_at.desc()
    ).first()

    # Get today's check-in status
    today_start = china_now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_logs = CheckinLog.query.filter(
        CheckinLog.user_id == user.id,
        CheckinLog.created_at >= today_start
    ).order_by(CheckinLog.created_at.desc()).all()

    today_status = "pending"
    today_message = ""
    if today_logs:
        for log in today_logs:
            if log.status == "success":
                today_status = "success"
                today_message = log.message
                break
            elif log.status == "already_done":
                today_status = "already_done"
                today_message = log.message
                break

    return jsonify({
        "credits": user.credits,
        "auto_checkin": user.auto_checkin,
        "today_status": today_status,
        "today_message": today_message,
        "latest_log": {
            "status": latest.status,
            "message": latest.message,
            "created_at": latest.created_at.isoformat() if latest else None,
        } if latest else None,
    })


# ─── Order API ───────────────────────────────────────────────────────────────

@app.route("/api/v1/orders", methods=["GET"])
@login_required
def api_orders():
    user = current_user
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
    return jsonify({
        "items": [
            {
                "id": o.id,
                "order_no": o.order_no,
                "amount": o.amount,
                "credits": o.credits,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "paid_at": o.paid_at.isoformat() if o.paid_at else None,
            }
            for o in orders
        ]
    })


@app.route("/api/v1/orders", methods=["POST"])
@login_required
def api_create_order():
    """Create a new order for purchasing credits."""
    if get_setting("payment_enabled", "true") != "true":
        return jsonify({"detail": "购买功能暂未开放"}), 400
    user = current_user
    order_no = uuid.uuid4().hex[:16]
    order = Order(
        user_id=user.id,
        order_no=order_no,
        amount=Config.PACKAGE_PRICE,
        credits=Config.PACKAGE_COUNT,
        status="pending",
    )
    db.session.add(order)
    db.session.commit()

    return jsonify({
        "id": order.id,
        "order_no": order.order_no,
        "amount": order.amount,
        "credits": order.credits,
        "status": order.status,
    }), 201


@app.route("/api/v1/orders/<int:order_id>/pay", methods=["POST"])
@login_required
def api_pay_order(order_id):
    """Simulate payment for an order. In production, integrate with a real payment gateway."""
    user = current_user
    order = Order.query.filter_by(id=order_id, user_id=user.id).first()
    if not order:
        return jsonify({"detail": "订单不存在"}), 404
    if order.status != "pending":
        return jsonify({"detail": "订单状态不允许支付"}), 400

    # Simulate successful payment
    order.status = "paid"
    order.paid_at = china_now()
    user.credits += order.credits
    db.session.commit()

    return jsonify({
        "message": "支付成功",
        "order_no": order.order_no,
        "credits_added": order.credits,
        "total_credits": user.credits,
    })


@app.route("/api/v1/orders/<int:order_id>", methods=["DELETE"])
@login_required
def api_delete_order(order_id):
    """Delete a pending order."""
    user = current_user
    order = Order.query.filter_by(id=order_id, user_id=user.id).first()
    if not order:
        return jsonify({"detail": "订单不存在"}), 404
    if order.status == "paid":
        return jsonify({"detail": "已支付订单不可删除"}), 400

    db.session.delete(order)
    db.session.commit()
    return jsonify({"message": "订单已删除"})


# ─── Announcement API ────────────────────────────────────────────────────────

@app.route("/api/v1/announcements")
def api_announcements():
    from sqlalchemy import or_
    page = request.args.get("page", "home")
    # Global: target_user_id IS NULL and page matches
    is_global = (Announcement.target_user_id == None) & (
        (Announcement.page == page) | (Announcement.page == "all")
    )
    if current_user.is_authenticated:
        # Also include personal announcements for this user
        is_personal = Announcement.target_user_id == current_user.id
        cond = is_global | is_personal
    else:
        cond = is_global

    items = Announcement.query.filter_by(active=True).filter(cond).order_by(
        Announcement.created_at.desc()
    ).all()

    return jsonify([
        {"id": a.id, "title": a.title, "content": a.content}
        for a in items
    ])


# ─── Admin routes ────────────────────────────────────────────────────────────

@app.route("/api/v1/admin/run-checkin", methods=["POST"])
def api_admin_run_checkin():
    """Run auto check-in for all users with auto_checkin enabled (triggered by scheduler)."""
    data = request.get_json() or {}
    admin_token = data.get("token", "")

    # Simple token auth for scheduler
    expected = hashlib.sha256(app.config["SECRET_KEY"].encode()).hexdigest()[:16]
    if admin_token != expected:
        return jsonify({"detail": "未授权"}), 403

    users = User.query.filter_by(auto_checkin=True, deleted_at=None).filter(User.credits > 0).all()
    results = []

    for user in users:
        try:
            campus_pw = decrypt_password(user.campus_password)
        except Exception:
            campus_pw = user.campus_password

        from services.checkin_service import run_checkin
        result_code, status_key, message = run_checkin(user.username, campus_pw)

        log = CheckinLog(user_id=user.id, status=status_key, message=message)
        db.session.add(log)

        if status_key == "success":
            user.credits = max(0, user.credits - 1)

        results.append({
            "username": user.username,
            "status": status_key,
            "message": message,
        })
    else:
        if not users:
            results.append({"message": "没有需要自动签到的用户"})

    db.session.commit()
    return jsonify({"results": results})


# ─── Admin User Management API ──────────────────────────────────────────────

@app.route("/api/v1/admin/users", methods=["GET"])
@admin_required
def admin_list_users():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    search = (request.args.get("search") or "").strip()

    query = User.query.filter_by(deleted_at=None)
    if search:
        query = query.filter(
            (User.username.contains(search)) | (User.email.contains(search))
        )

    total = query.count()
    users = query.order_by(User.id.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "credits": u.credits,
                "auto_checkin": u.auto_checkin,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "login_count": CheckinLog.query.filter_by(user_id=u.id).count(),
                "last_checkin": (
                    CheckinLog.query.filter_by(user_id=u.id)
                    .order_by(CheckinLog.created_at.desc())
                    .first().created_at.isoformat()
                ) if CheckinLog.query.filter_by(user_id=u.id).first() else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "pages": max(1, (total + per_page - 1) // per_page),
    })


@app.route("/api/v1/admin/users/<int:user_id>/credits", methods=["PUT"])
@admin_required
def admin_adjust_credits(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    delta = data.get("delta", 0)  # positive = add, negative = deduct
    reason = (data.get("reason") or "").strip()

    if not isinstance(delta, int) or delta == 0:
        return jsonify({"detail": "请输入有效的增减数值"}), 422

    new_credits = max(0, user.credits + delta)
    user.credits = new_credits
    db.session.commit()

    return jsonify({
        "message": f"已{'增加' if delta > 0 else '减少'} {abs(delta)} 次签到次数",
        "username": user.username,
        "previous": user.credits - delta,
        "current": new_credits,
    })


@app.route("/api/v1/admin/users/simple", methods=["GET"])
@admin_required
def admin_users_simple():
    """Simple user list for announcement targeting dropdown."""
    users = User.query.filter_by(deleted_at=None).order_by(User.id).all()
    return jsonify([
        {"id": u.id, "username": u.username}
        for u in users
    ])


# ─── Admin Page Routes ──────────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin_page():
    return render_template("admin.html", page="overview")


@app.route("/admin/settings")
@admin_required
def admin_settings_page():
    return render_template("admin.html", page="settings")


@app.route("/admin/announcements")
@admin_required
def admin_announcements_page():
    return render_template("admin.html", page="announcements")


@app.route("/admin/users")
@admin_required
def admin_users_page():
    return render_template("admin.html", page="users")


# ─── Admin API Routes ───────────────────────────────────────────────────────

@app.route("/api/v1/admin/settings", methods=["GET"])
@admin_required
def admin_get_settings():
    settings = []
    for s in SiteSetting.query.order_by(SiteSetting.key).all():
        settings.append({
            "key": s.key,
            "value": s.value,
            "description": s.description,
        })
    return jsonify({"settings": settings})


@app.route("/api/v1/admin/settings", methods=["PUT"])
@admin_required
def admin_update_settings():
    data = request.get_json() or {}
    updates = data.get("settings", {})
    if not updates:
        return jsonify({"detail": "请提供要更新的设置"}), 422

    for key, value in updates.items():
        s = SiteSetting.query.filter_by(key=key).first()
        if s:
            s.value = str(value)
            db.session.commit()

    return jsonify({"message": "设置已更新"})


@app.route("/api/v1/admin/overview", methods=["GET"])
@admin_required
def admin_overview():
    total_users = User.query.filter_by(deleted_at=None).count()
    total_checkins = CheckinLog.query.filter_by(status="success").count()
    today_start = china_now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_checkins = CheckinLog.query.filter(
        CheckinLog.status == "success",
        CheckinLog.created_at >= today_start
    ).count()
    auto_users = User.query.filter_by(auto_checkin=True, deleted_at=None).count()

    recent_logs = (
        CheckinLog.query
        .order_by(CheckinLog.created_at.desc())
        .limit(20)
        .all()
    )

    return jsonify({
        "total_users": total_users,
        "total_checkins": total_checkins,
        "today_checkins": today_checkins,
        "auto_users": auto_users,
        "recent_logs": [
            {
                "username": User.query.get(log.user_id).username if User.query.get(log.user_id) else "已删除",
                "status": log.status,
                "message": log.message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in recent_logs
        ],
    })


@app.route("/api/v1/admin/announcements", methods=["GET"])
@admin_required
def admin_list_announcements():
    items = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return jsonify({
        "items": [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "page": a.page,
                "target_user_id": a.target_user_id,
                "active": a.active,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in items
        ]
    })


@app.route("/api/v1/admin/announcements", methods=["POST"])
@admin_required
def admin_create_announcement():
    data = request.get_json() or {}
    target_uid = data.get("target_user_id")
    a = Announcement(
        title=data.get("title", ""),
        content=data.get("content", ""),
        page=data.get("page", "home"),
        target_user_id=target_uid if target_uid else None,
        active=data.get("active", True),
    )
    db.session.add(a)
    db.session.commit()
    return jsonify({"message": "公告已创建", "id": a.id}), 201


@app.route("/api/v1/admin/announcements/<int:aid>", methods=["PUT"])
@admin_required
def admin_update_announcement(aid):
    a = Announcement.query.get_or_404(aid)
    data = request.get_json() or {}
    for field in ["title", "content", "page"]:
        if field in data:
            setattr(a, field, data[field])
    if "target_user_id" in data:
        tu = data["target_user_id"]
        a.target_user_id = tu if tu else None
    if "active" in data:
        a.active = data["active"]
    db.session.commit()
    return jsonify({"message": "公告已更新"})


@app.route("/api/v1/admin/announcements/<int:aid>", methods=["DELETE"])
@admin_required
def admin_delete_announcement(aid):
    a = Announcement.query.get_or_404(aid)
    db.session.delete(a)
    db.session.commit()
    return jsonify({"message": "公告已删除"})


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    # Start scheduler for auto check-in
    try:
        from scheduler import start_scheduler
        scheduler = start_scheduler(app)
    except ImportError as e:
        print(f"[WARNING] 无法启动调度器: {e}")
        print("安装 apscheduler: pip install apscheduler>=3.10.0")
        scheduler = None

    print("=" * 50)
    print("签到系统 Web 服务启动中...")
    print("访问 http://127.0.0.1:5000")
    print("=" * 50)

    port = int(os.environ.get("PORT", 5000))
    try:
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        if scheduler:
            scheduler.shutdown()

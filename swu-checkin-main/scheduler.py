"""
Auto check-in scheduler.
Runs daily at 21:10 Beijing time, processing all users with auto_checkin enabled.
Can be run standalone or as part of the Flask app.
"""
import hashlib
import sys
import os

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))


def run_scheduled_checkin(app):
    """Run check-in for all auto-enabled users via the app's API."""
    with app.app_context():
        from models import db, User, CheckinLog, china_now
        from services.checkin_service import run_checkin

        # Build admin token
        admin_token = hashlib.sha256(app.config["SECRET_KEY"].encode()).hexdigest()[:16]

        users = (
            User.query
            .filter_by(auto_checkin=True, deleted_at=None)
            .filter(User.credits > 0)
            .all()
        )

        results = []
        for user in users:
            try:
                from app import decrypt_password
                campus_pw = decrypt_password(user.campus_password)
            except Exception:
                campus_pw = user.campus_password

            try:
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
            except Exception as e:
                results.append({
                    "username": user.username,
                    "status": "error",
                    "message": str(e),
                })

        db.session.commit()

        if results:
            print(f"[Scheduler] Processed {len(results)} users: {results}")
        else:
            print("[Scheduler] No users to process")
        return results


def start_scheduler(app):
    """Start APScheduler with the Flask app."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler()

    @scheduler.scheduled_job(
        CronTrigger(hour=app.config.get("CHECKIN_HOUR", 21), minute=app.config.get("CHECKIN_MINUTE", 10),
                     timezone="Asia/Shanghai"),
        id="auto_checkin",
        name="Daily auto check-in",
    )
    def auto_checkin_job():
        print("[Scheduler] Starting daily auto check-in...")
        try:
            run_scheduled_checkin(app)
        except Exception as e:
            print(f"[Scheduler] Error: {e}")

    scheduler.start()
    print(f"[Scheduler] Started. Auto check-in scheduled daily at "
          f"{app.config.get('CHECKIN_HOUR', 21):02d}:{app.config.get('CHECKIN_MINUTE', 10):02d} Beijing time.")
    return scheduler

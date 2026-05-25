import sys
import os
import threading
import time as _time

# Add scripts directory to path so we can import from it
_SCRIPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

STATUS_MAP = {
    0: ("no_task", "今日暂无签到任务"),
    1: ("success", "签到成功"),
    2: ("already_done", "今日已签到，无需重复操作"),
    3: ("auth_error", "账号或密码验证失败"),
    4: ("network_error", "连接错误或请求超时"),
    5: ("vacation", "请假中，无需签到"),
}


def run_checkin(username, password, timeout=10):
    """Run check-in synchronously. Returns (status_code, status_key, message)."""
    from check_in import check_in
    result = check_in(username, password, timeout)
    status_key, message = STATUS_MAP.get(result, ("unknown", f"未知结果: {result}"))
    return result, status_key, message


def run_checkin_threaded(username, password, callback=None, timeout=10):
    """Run check-in in a background thread. Calls callback(status_code, status_key, message) when done."""
    def _run():
        result_code, status_key, message = None, "error", "签到处理异常"
        try:
            result_code, status_key, message = run_checkin(username, password, timeout)
        except Exception as e:
            message = f"签到异常: {str(e)}"
        if callback:
            callback(result_code, status_key, message)
        return result_code, status_key, message

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread

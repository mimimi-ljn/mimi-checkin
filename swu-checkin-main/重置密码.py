"""Standalone script to reset a user's password directly in the SQLite database.
Use this when you can't log in (e.g. after encryption key issues).

Usage:
    python 重置密码.py             # reset user ID 1 (admin) to default password
    python 重置密码.py 2           # reset user ID 2
    python 重置密码.py 1 mypass    # reset user ID 1 with custom password
"""
import os
import sys
import base64
import hashlib

# ── Encryption (same as app.py, uses hardcoded key to be independent) ──
_ENCRYPTION_KEY = "change-me-to-a-r"


def _simple_encrypt(password):
    result = []
    for i, c in enumerate(password):
        kc = ord(_ENCRYPTION_KEY[i % len(_ENCRYPTION_KEY)])
        result.append(chr(ord(c) ^ kc))
    return base64.urlsafe_b64encode("".join(result).encode()).decode()


def encrypt_password(password):
    try:
        from cryptography.fernet import Fernet
        key = _ENCRYPTION_KEY.encode()
        f = Fernet(base64.urlsafe_b64encode(key.ljust(32, b"0")[:32]))
        return f.encrypt(password.encode()).decode()
    except (ImportError, Exception):
        return _simple_encrypt(password)


# ── Find and open database ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "app.db")

if not os.path.exists(db_path):
    # Try instance folder
    instance_path = os.path.join(BASE_DIR, "instance", "app.db")
    if os.path.exists(instance_path):
        db_path = instance_path
    else:
        print(f"错误：找不到数据库文件 app.db")
        print(f"尝试过：{db_path}")
        print(f"尝试过：{instance_path}")
        sys.exit(1)

# Use sqlite3 directly (no Flask dependency needed)
import sqlite3

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# ── Get target user ──
user_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
new_password = sys.argv[2] if len(sys.argv) > 2 else "admin123"

# Check user exists
cursor.execute("SELECT id, username, email FROM users WHERE id = ? AND deleted_at IS NULL", (user_id,))
row = cursor.fetchone()
if not row:
    print(f"错误：找不到用户 ID={user_id}")
    conn.close()
    sys.exit(1)

uid, username, email = row

# Encrypt and update
encrypted = encrypt_password(new_password)
cursor.execute("UPDATE users SET campus_password = ? WHERE id = ?", (encrypted, user_id))
conn.commit()
conn.close()

print("=" * 40)
print("密码重置成功！")
print(f"  用户 ID: {uid}")
print(f"  用户名:  {username}")
print(f"  邮箱:    {email}")
print(f"  新密码:  {new_password}")
print("=" * 40)
print()
print("请用新密码登录后立即修改密码。")

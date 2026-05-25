import sqlite3
import os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.db')
conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=" * 70)
print("                        数据库查看工具")
print("=" * 70)

# ── 用户 ──
cur.execute('SELECT id, username, email, credits, auto_checkin, terms_accepted, created_at FROM users WHERE deleted_at IS NULL ORDER BY id')
users = cur.fetchall()
print(f"\n{'='*70}")
print(f"  用户列表（共 {len(users)} 人）")
print(f"{'='*70}")
print(f"  {'ID':<4} {'用户名':<16} {'邮箱':<28} {'积分':<6} {'自动签到':<8} {'注册时间'}")
print(f"  {'-'*66}")
for u in users:
    auto = '是' if u[4] else '否'
    print(f"  {u[0]:<4} {u[1] or '':<16} {u[2] or '':<28} {u[3] or 0:<6} {auto:<8} {u[6] or ''}")

# ── 签到日志 ──
cur.execute('SELECT id, user_id, status, message, created_at FROM checkin_logs ORDER BY created_at DESC LIMIT 20')
logs = cur.fetchall()
print(f"\n{'='*70}")
print(f"  签到日志（最近 {len(logs)} 条，共 {cur.execute('SELECT COUNT(*) FROM checkin_logs').fetchone()[0]} 条）")
print(f"{'='*70}")
if logs:
    for l in logs:
        print(f"  [{l[4]}] 用户ID:{l[1]}  状态:{l[2]}  信息:{l[3]}")
else:
    print("  （暂无记录）")

# ── 订单 ──
cur.execute('SELECT id, user_id, order_no, amount, credits, status, created_at FROM orders ORDER BY created_at DESC')
orders = cur.fetchall()
print(f"\n{'='*70}")
print(f"  订单列表（共 {len(orders)} 条）")
print(f"{'='*70}")
if orders:
    for o in orders:
        print(f"  [{o[6]}] 用户ID:{o[1]}  编号:{o[2]}  金额:{o[3]}  积分:{o[4]}  状态:{o[5]}")
else:
    print("  （暂无记录）")

# ── 公告 ──
cur.execute('SELECT id, title, created_at FROM announcements ORDER BY created_at DESC')
anns = cur.fetchall()
print(f"\n{'='*70}")
print(f"  公告列表（共 {len(anns)} 条）")
print(f"{'='*70}")
if anns:
    for a in anns:
        print(f"  [{a[2]}] {a[1]}")
else:
    print("  （暂无记录）")

print(f"\n{'='*70}")
conn.close()
input("\n按回车键退出...")

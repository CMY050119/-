#!/usr/bin/env python3
"""
每周磁盘清理脚本 — 清理临时/缓存文件，邮件报告清理结果。
用法：python weekly_cleanup.py
"""

import os
import shutil
import smtplib
import ssl
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# 修复 Windows GBK 终端 Unicode 输出
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BJ = timezone(timedelta(hours=8))

# SMTP
SMTP_SERVER = "smtp.qq.com"
SENDER = "changmengyang2005@qq.com"
RECEIVER = "changmengyang2005@qq.com"
AUTH_CODE = "sbjcsttjivgudede"

# 清理目标（路径, 说明, 是否安全可删）
TARGETS = [
    ("E:\\DeliveryOptimization",       "Windows 更新分发缓存", True),
    ("F:\\amd录制视频",                 "AMD 游戏录制视频",    True),
    (os.path.expandvars(r"%LOCALAPPDATA%\Temp"), "系统临时文件", True),
    (os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cache"), "Edge 浏览器缓存", True),
    (os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Code Cache"), "Edge Code 缓存", True),
    ("C:\\DrvPath",                     "旧版驱动安装包",      True),
]

# 游戏缓存目录（可能有进程占用，尽力清）
GAME_CACHE = "E:\\游戏缓存——————————"


def get_dir_size(path: str) -> int:
    """返回目录总字节数。"""
    if not os.path.exists(path):
        return 0
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def clean_dir(path: str) -> int:
    """清空目录内容，返回清理字节数。不存在则返回 0。"""
    if not os.path.exists(path):
        return 0
    before = get_dir_size(path)
    if before == 0:
        return 0
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path, ignore_errors=True)
        except Exception:
            pass
    after = get_dir_size(path)
    return before - after


def empty_recycle_bin() -> int:
    """清空回收站，返回清除项数。"""
    count = 0
    try:
        import winshell
        count = winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
    except Exception:
        # 用 cmd 兜底
        for drive in ["C:", "E:", "F:"]:
            subprocess.run(f'cmd /c "rd /s /q {drive}\\$Recycle.bin 2>nul"', shell=True)
    return count


def send_report(records: list, total_bytes: int):
    """发送清理报告邮件。"""
    now = datetime.now(BJ)
    date_str = now.strftime("%Y-%m-%d %H:%M")
    total_gb = total_bytes / (1024**3)

    rows = ""
    for name, before_gb, after_gb, cleaned_gb, note in records:
        rows += (
            f"<tr><td style='padding:6px 12px;border-bottom:1px solid #eee;'>{name}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #eee;text-align:right;'>{before_gb:.2f}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #eee;text-align:right;'>{after_gb:.2f}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #eee;text-align:right;color:#d32f2f;'>{cleaned_gb:.2f}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #eee;font-size:12px;color:#888;'>{note}</td></tr>"
        )

    html = f"""<html><head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;background:#f5f5f5;padding:20px;">
<div style="max-width:640px;margin:0 auto;background:#fff;border-radius:10px;padding:28px;box-shadow:0 2px 12px rgba(0,0,0,.08);">
<h1 style="font-size:20px;color:#333;margin:0 0 4px;">🧹 每周磁盘清理报告</h1>
<p style="color:#999;font-size:13px;margin:0 0 20px;">{date_str}</p>
<table style="width:100%;border-collapse:collapse;font-size:14px;">
<tr style="background:#fafafa;"><th style="padding:8px 12px;text-align:left;border-bottom:2px solid #ddd;">清理项目</th>
<th style="padding:8px 12px;text-align:right;border-bottom:2px solid #ddd;">清理前</th>
<th style="padding:8px 12px;text-align:right;border-bottom:2px solid #ddd;">清理后</th>
<th style="padding:8px 12px;text-align:right;border-bottom:2px solid #ddd;">释放空间</th>
<th style="padding:8px 12px;text-align:left;border-bottom:2px solid #ddd;">备注</th></tr>
{rows}
</table>
<p style="margin:20px 0 0;font-size:16px;font-weight:700;color:#d32f2f;">本次共释放: {total_gb:.1f} GB</p>
<p style="color:#bbb;font-size:12px;margin:20px 0 0;text-align:center;">每周四 12:00 自动执行 &nbsp;|&nbsp; 保留微信缓存，不删重要文件</p>
</div></body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"磁盘清理报告 · {now.strftime('%Y-%m-%d')}"
    msg["From"] = SENDER
    msg["To"] = RECEIVER
    msg.attach(MIMEText(html, "html", "utf-8"))

    ctx = ssl.create_default_context()
    for port, use_ssl in [(587, False), (465, True)]:
        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(SMTP_SERVER, port, context=ctx, timeout=15)
            else:
                server = smtplib.SMTP(SMTP_SERVER, port, timeout=15)
                server.ehlo()
                server.starttls(context=ctx)
                server.ehlo()
            server.login(SENDER, AUTH_CODE)
            server.sendmail(SENDER, [RECEIVER], msg.as_string())
            server.quit()
            return
        except Exception as e:
            try:
                server.quit()
            except Exception:
                pass


def main():
    now = datetime.now(BJ)
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 开始每周磁盘清理...")

    records = []
    total_cleaned = 0

    for path, desc, _ in TARGETS:
        before = get_dir_size(path)
        cleaned = clean_dir(path)
        after = get_dir_size(path)
        total_cleaned += cleaned
        records.append((
            desc,
            before / (1024**3),
            after / (1024**3),
            cleaned / (1024**3),
            path
        ))
        print(f"  {desc}: {cleaned/(1024**3):.2f} GB")

    # 游戏缓存（可能有锁定文件，尽力清理）
    if os.path.exists(GAME_CACHE):
        before = get_dir_size(GAME_CACHE)
        cleaned = clean_dir(GAME_CACHE)
        after = get_dir_size(GAME_CACHE)
        total_cleaned += cleaned
        records.append((
            "游戏安装缓存",
            before / (1024**3),
            after / (1024**3),
            cleaned / (1024**3),
            GAME_CACHE
        ))
        print(f"  游戏缓存: {cleaned/(1024**3):.2f} GB")

    # 回收站
    try:
        rb_count = empty_recycle_bin()
        if rb_count:
            print(f"  回收站: {rb_count} 项")
            records.append(("回收站", 0, 0, 0, f"清空 {rb_count} 项"))
    except Exception:
        pass

    total_gb = total_cleaned / (1024**3)
    print(f"  总计释放: {total_gb:.1f} GB")

    if total_gb > 0.01:
        print("  发送报告邮件...")
        send_report(records, total_cleaned)
        print("  [OK] 报告已发送")
    else:
        print("  无需清理，跳过邮件")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
AI HOT 实时日报 — 邮件 + 微信测试号双通道推送。
用法：python ai_daily_email.py
"""

import json
import os
import smtplib
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ============================================================
# 邮箱配置（优先环境变量，兼容原硬编码）
# ============================================================
SMTP_SERVER = "smtp.qq.com"
SENDER = os.environ.get("SMTP_SENDER", "changmengyang2005@qq.com")
RECEIVER = os.environ.get("SMTP_RECEIVER", "changmengyang2005@qq.com")
AUTH_CODE = os.environ.get("SMTP_AUTH_CODE", "sbjcsttjivgudede")

# ============================================================
# 微信测试号配置（优先环境变量，兼容原硬编码）
# ============================================================
WX_APPID = os.environ.get("WX_APPID", "wx690351c82e0d0129")
WX_SECRET = os.environ.get("WX_SECRET", "5b15e6173e23e109cc23da97c31a86a0")
WX_OPENID = os.environ.get("WX_OPENID", "o7YP22-68lYQwL-ONRVjFenxRsJY")
WX_TEMPLATE_ID = os.environ.get("WX_TEMPLATE_ID", "RuPAAS_yjeZx4L9KdYnRkMTxwuYtcxboWhygzE6gDZc")
WX_TOKEN_API = "https://api.weixin.qq.com/cgi-bin/token"
WX_SEND_API = "https://api.weixin.qq.com/cgi-bin/message/template/send"

_wx_token = {"token": "", "expires_at": 0}

# ============================================================
# API / 时间
# ============================================================
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
API_ITEMS = "https://aihot.virxact.com/api/public/items"
BJ = timezone(timedelta(hours=8))

CAT_LABELS = {
    "ai-models":  "模型发布/更新",
    "ai-products": "产品发布/更新",
    "industry":   "行业动态",
    "paper":      "论文研究",
    "tip":        "技巧与观点",
}
CAT_ORDER = ["ai-models", "ai-products", "industry", "paper", "tip"]


# ============================================================
# 工具
# ============================================================
def ts_to_human(iso: str) -> str:
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        local = t.astimezone(BJ)
        now_bj = datetime.now(BJ)
        wday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][local.weekday()]
        hm = local.strftime("%H:%M")
        diff = (now_bj - local).total_seconds()
        if diff < 60:       return "刚刚"
        if diff < 3600:     return f"{int(diff // 60)} 分钟前"
        if diff < 7200:     return f"1 小时 {int((diff - 3600) // 60)} 分钟前"
        if diff < 3600 * 6: return f"{int(diff // 3600)} 小时前"
        if local.date() == now_bj.date(): return f"今天 {hm}"
        yesterday = now_bj.date() - timedelta(days=1)
        if local.date() == yesterday: return f"昨天 {hm}"
        return f"{local.strftime('%m/%d')} {wday} {hm}"
    except Exception:
        return iso


def truncate(s: str, n: int = 280) -> str:
    return s if len(s) <= n else s[:n] + "…"


def fetch_items() -> dict:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {"mode": "selected", "since": since, "take": "50"}
    url = f"{API_ITEMS}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    items = result.get("items", [])

    if len(items) < 5:
        since = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        params["since"] = since
        url = f"{API_ITEMS}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        items = result.get("items", [])

    return {"items": items, "fetched_at": now.isoformat()}


# ============================================================
# 微信推送
# ============================================================
def _wx_get_token() -> str:
    now_ts = datetime.now().timestamp()
    if _wx_token["token"] and now_ts < _wx_token["expires_at"]:
        return _wx_token["token"]
    params = urllib.parse.urlencode({
        "grant_type": "client_credential",
        "appid": WX_APPID,
        "secret": WX_SECRET,
    })
    url = f"{WX_TOKEN_API}?{params}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    _wx_token["token"] = body.get("access_token", "")
    _wx_token["expires_at"] = now_ts + body.get("expires_in", 7200) - 300
    return _wx_token["token"]


def push_to_wechat(items: list, date_str: str) -> bool:
    if not items:
        return False

    top = []
    for it in items[:5]:
        top.append(f"  · {it.get('title', '')[:40]}")
    digest = "\n".join(top)

    cats = {}
    for it in items:
        c = it.get("category", "other")
        cats[c] = cats.get(c, 0) + 1
    cat_str = "  ".join(f"{CAT_LABELS.get(k, k)}×{v}" for k, v in sorted(cats.items()))

    now_str = datetime.now(BJ).strftime("%H:%M")

    body = json.dumps({
        "touser": WX_OPENID,
        "template_id": WX_TEMPLATE_ID,
        "data": {
            "first": {
                "value": f"AI HOT 实时 · {date_str}\n\n{cat_str}\n共 {len(items)} 条精选\n\n{digest}\n\n点击下方查看完整日报 →",
                "color": "#333333",
            },
            "keyword1": {"value": f"{len(items)} 条", "color": "#1565c0"},
            "keyword2": {"value": f"{date_str} {now_str}", "color": "#888888"},
            "remark": {
                "value": "\n来源: aihot.virxact.com\n每天 9:00/14:00/18:00 自动推送\n邮箱同步: changmengyang2005@qq.com",
                "color": "#999999",
            },
        },
    }, ensure_ascii=False).encode("utf-8")

    token = _wx_get_token()
    url = f"{WX_SEND_API}?access_token={token}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("errcode") == 0


# ============================================================
# HTML 邮件构建
# ============================================================
BASIC_CSS = """
body { margin:0; padding:20px; background:#f5f5f5; font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif; }
.card-wrap { max-width:680px; margin:0 auto; background:#fff; border-radius:10px; padding:32px 28px; box-shadow:0 2px 12px rgba(0,0,0,.08); }
h1 { margin:0 0 4px; font-size:22px; color:#d32f2f; }
.subtitle { margin:0 0 24px; color:#999; font-size:13px; }
h2 { margin:28px 0 10px; font-size:17px; padding-left:10px; border-left:4px solid; color:#333; }
.item { margin:0 0 14px; padding:0 0 12px; border-bottom:1px solid #eee; }
.item-title { font-size:14px; font-weight:600; margin:0 0 2px; color:#222; }
.item-source { font-size:12px; color:#888; margin:0 0 4px; }
.item-summary { font-size:13px; color:#444; line-height:1.65; margin:0 0 4px; }
.item-url { font-size:11px; }
.item-url a { color:#1976d2; text-decoration:none; }
.foot { margin-top:24px; padding-top:12px; border-top:1px solid #eee; font-size:12px; color:#bbb; text-align:center; }
"""

SEC_COLORS = {
    "模型发布/更新": "#1565c0",
    "产品发布/更新": "#6a1b9a",
    "行业动态":       "#e65100",
    "论文研究":       "#2e7d32",
    "技巧与观点":     "#c62828",
}


def build_html(items: list) -> str:
    groups = {}
    for item in items:
        cat = item.get("category", "tip")
        groups.setdefault(cat, []).append(item)

    now_bj = datetime.now(BJ)
    date_str = now_bj.strftime("%Y-%m-%d")

    lines = [
        '<html><head><meta charset="utf-8">',
        f'<style>{BASIC_CSS}</style></head><body>',
        '<div class="card-wrap">',
        f'<h1>AI HOT 实时 · {date_str}</h1>',
        f'<p class="subtitle">生成时间：{now_bj.strftime("%H:%M")}  |  过去 6h 精选（不足扩至 24h） |  共 {len(items)} 条  |  已推送到微信</p>',
    ]

    idx = 0
    for cat in CAT_ORDER:
        cat_items = groups.pop(cat, [])
        if not cat_items:
            continue
        label = CAT_LABELS.get(cat, cat)
        color = SEC_COLORS.get(label, "#333")
        lines.append(f'<h2 style="color:{color};border-left-color:{color};">{label}（{len(cat_items)} 条）</h2>')
        for item in cat_items:
            idx += 1
            title = item.get("title", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            source = item.get("source", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            summary = item.get("summary", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            url = item.get("url", "").replace("&", "&amp;").replace('"', "&quot;")
            pub = item.get("publishedAt", "")

            lines.append('<div class="item">')
            lines.append(f'<p class="item-title">{idx}. {title}</p>')
            lines.append(f'<p class="item-source">来源：{source} · {ts_to_human(pub)}</p>')
            lines.append(f'<p class="item-summary">{truncate(summary, 280)}</p>')
            if url:
                lines.append(f'<p class="item-url"><a href="{url}">查看原文 →</a></p>')
            lines.append('</div>')

    for cat, cat_items in groups.items():
        label = CAT_LABELS.get(cat, cat)
        color = SEC_COLORS.get(label, "#333")
        lines.append(f'<h2 style="color:{color};border-left-color:{color};">{label}（{len(cat_items)} 条）</h2>')
        for item in cat_items:
            idx += 1
            title = item.get("title", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            source = item.get("source", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            summary = item.get("summary", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            url = item.get("url", "").replace("&", "&amp;").replace('"', "&quot;")
            pub = item.get("publishedAt", "")

            lines.append('<div class="item">')
            lines.append(f'<p class="item-title">{idx}. {title}</p>')
            lines.append(f'<p class="item-source">来源：{source} · {ts_to_human(pub)}</p>')
            lines.append(f'<p class="item-summary">{truncate(summary, 280)}</p>')
            if url:
                lines.append(f'<p class="item-url"><a href="{url}">查看原文 →</a></p>')
            lines.append('</div>')

    lines.append(
        '<div class="foot">本日报由 AI HOT API 自动生成  |  '
        '数据来源 <a href="https://aihot.virxact.com" style="color:#1976d2;">aihot.virxact.com</a>  |  '
        '已推送到微信服务号</div>'
    )
    lines.append('</div></body></html>')
    return "\n".join(lines)


# ============================================================
# SMTP
# ============================================================
def _smtp_send(msg):
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
            print(f"  [WARN] 端口 {port} 失败: {e}")
            try:
                server.quit()
            except Exception:
                pass
    raise RuntimeError("所有 SMTP 端口均连接失败")


def send_email(items: list, date_str: str):
    html = build_html(items)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"AI HOT 实时 · {date_str}"
    msg["From"] = SENDER
    msg["To"] = RECEIVER
    msg.attach(MIMEText(html, "html", "utf-8"))
    _smtp_send(msg)
    return html


# ============================================================
# 主流程
# ============================================================
def main():
    now = datetime.now(BJ)
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 开始抓取 AI HOT 实时精选...")
    data = fetch_items()
    items = data.get("items", [])
    if not items:
        print("  [WARN] 无实时数据，跳过发送")
        return

    date_str = now.strftime("%Y-%m-%d")
    print(f"  [OK] 获取成功: {date_str}, 共 {len(items)} 条")

    cats = {}
    for it in items:
        c = it.get("category", "other")
        cats[c] = cats.get(c, 0) + 1
    for c, n in sorted(cats.items()):
        print(f"    {CAT_LABELS.get(c, c)}: {n} 条")

    print("  发送邮件...")
    html = send_email(items, date_str)
    print(f"  [OK] 邮件发送成功 ({len(html)} 字符)")

    print("  推送微信模板消息...")
    ok = push_to_wechat(items, date_str)
    print(f"  {'[OK] 微信推送成功' if ok else '[WARN] 微信推送失败'}")


if __name__ == "__main__":
    main()

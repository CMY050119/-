"""
仿百度搜索引擎 - Flask 后端
搜索功能 + 邮件发送
"""
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from flask import Flask, render_template, request, jsonify
from ddgs import DDGS

from config import (
    SMTP_SENDER, SMTP_PASSWORD, SMTP_HOST, SMTP_PORT,
    SEARCH_MAX_RESULTS, SECRET_KEY, DEBUG
)

app = Flask(__name__)
app.secret_key = SECRET_KEY


# ============================================
# 路由：首页
# ============================================
@app.route("/")
def index():
    """渲染仿百度搜索首页"""
    return render_template("index.html")


# ============================================
# API：搜索
# ============================================
@app.route("/api/search")
def search():
    """搜索 API，返回 JSON 结果"""
    query = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    max_results = min(int(request.args.get("max", SEARCH_MAX_RESULTS)), 50)

    if not query:
        return jsonify({"error": "请输入搜索关键词", "results": [], "total": 0})

    try:
        results = []
        # timeout=15 秒防止网络问题卡死
        with DDGS(timeout=15) as ddgs:
            search_results = list(ddgs.text(
                query,
                max_results=max_results,
            ))

            for r in search_results:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })

        total = len(results)

        # 简单分页（前端处理）
        per_page = 10
        start = (page - 1) * per_page
        end = start + per_page
        paged_results = results[start:end]

        return jsonify({
            "query": query,
            "results": paged_results,
            "total": total,
            "page": page,
            "has_more": end < total,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    except Exception as e:
        app.logger.error(f"搜索出错: {str(e)}")
        return jsonify({
            "error": f"搜索服务暂时不可用，请稍后重试",
            "results": [],
            "total": 0
        }), 500


# ============================================
# API：发送搜索结果到邮箱
# ============================================
@app.route("/api/send-email", methods=["POST"])
def send_email():
    """将搜索结果发送到指定邮箱"""
    data = request.get_json()
    target_email = data.get("email", "").strip()
    query = data.get("query", "").strip()
    results = data.get("results", [])

    if not target_email:
        return jsonify({"success": False, "message": "请输入邮箱地址"}), 400

    if not results:
        return jsonify({"success": False, "message": "没有搜索结果可发送"}), 400

    # 检查 SMTP 是否已配置
    if not SMTP_PASSWORD or "your_email" in SMTP_SENDER:
        return jsonify({
            "success": False,
            "message": "邮件服务未配置，请在 config.py 或 .env 中设置 SMTP 信息"
        }), 500

    try:
        # 构建 HTML 邮件内容
        html_content = build_email_html(query, results, target_email)

        # 创建邮件
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f'搜索结果: {query} - 共 {len(results)} 条'
        msg["From"] = SMTP_SENDER
        msg["To"] = target_email
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # 发送邮件
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_SENDER, SMTP_PASSWORD)
            server.sendmail(SMTP_SENDER, target_email, msg.as_string())

        return jsonify({
            "success": True,
            "message": f"搜索结果已发送到 {target_email}，请查收！"
        })

    except smtplib.SMTPAuthenticationError:
        return jsonify({
            "success": False,
            "message": "邮箱认证失败，请检查邮箱地址和密码/授权码是否正确"
        }), 500
    except Exception as e:
        app.logger.error(f"邮件发送失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"邮件发送失败: {str(e)}"
        }), 500


def build_email_html(query, results, target_email):
    """构建搜索结果 HTML 邮件"""
    results_html = ""
    for i, r in enumerate(results, 1):
        results_html += f"""
        <div style="margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #eee;">
            <h3 style="margin: 0 0 5px 0;">
                <a href="{r['url']}" target="_blank"
                   style="color: #1a0dab; text-decoration: none; font-size: 16px;">
                    {r['title']}
                </a>
            </h3>
            <div style="color: #006621; font-size: 13px; margin-bottom: 3px;">
                {r['url'][:80]}{'...' if len(r['url']) > 80 else ''}
            </div>
            <p style="color: #545454; font-size: 14px; line-height: 1.6; margin: 3px 0;">
                {r['snippet']}
            </p>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: 'Microsoft YaHei', Arial, sans-serif;
          max-width: 700px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
        <div style="background: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <h1 style="color: #3385ff; text-align: center; font-size: 28px; margin-bottom: 5px;">
                🔍 AI 搜索引擎
            </h1>
            <p style="text-align: center; color: #999; margin-bottom: 25px;">
                搜索关键词：<strong style="color: #c00;">{query}</strong> |
                结果数量：{len(results)} 条 |
                发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
            </p>
            {results_html}
            <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
            <p style="color: #999; font-size: 12px; text-align: center;">
                此邮件由 AI 搜索引擎自动发送至 {target_email}<br>
                如有问题请联系管理员
            </p>
        </div>
    </body>
    </html>"""


# ============================================
# 启动服务器
# ============================================
if __name__ == "__main__":
    import sys
    # 设置 stdout 编码为 UTF-8，避免中文/emoji 输出报错
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 50)
    print("   [AI] 仿百度搜索引擎已启动")
    print("   访问地址: http://localhost:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)

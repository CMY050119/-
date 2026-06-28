"""
配置文件 - 邮箱 SMTP 设置
请填写你的邮箱信息后使用
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# 邮箱 SMTP 配置（发送搜索结果用）
# ============================================
# 发送方邮箱
SMTP_SENDER = os.getenv("SMTP_SENDER", "your_email@gmail.com")
# SMTP 密码（Gmail 需要用应用专用密码，QQ邮箱用授权码）
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
# SMTP 服务器地址
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
# SMTP 端口（Gmail: 587, QQ: 587）
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# ============================================
# 搜索引擎配置
# ============================================
# 每次搜索返回的结果数量
SEARCH_MAX_RESULTS = 20

# Flask 配置
SECRET_KEY = os.getenv("SECRET_KEY", "baidu-search-demo-secret-key")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

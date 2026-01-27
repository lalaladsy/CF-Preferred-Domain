#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
from datetime import datetime

# 配置
API_URL = "https://vps789.com/openApi/cfIpTop20"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def fetch_top_domains():
    """获取优选域名数据"""
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 0:
            return data.get("data", {}).get("good", [])[:10]
        return None
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        return None

def format_message(domains):
    """格式化Telegram消息"""
    if not domains:
        return "⚠️ 今日暂无数据"
    
    # 获取数据时间
    data_time = domains[0].get("createdTime", "未知")
    
    message = f"🌐 <b>Cloudflare优选域名 TOP 5</b>\n"
    message += f"📅 数据时间: <code>{data_time}</code>\n"
    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    
    for idx, domain in enumerate(domains):
        ip = domain.get("ip", "N/A")
        avg_latency = domain.get("avgLatency", 0)
        avg_loss = domain.get("avgPkgLostRate", 0)
        
        # 三网数据
        yd_latency = domain.get("ydLatency", 0)
        lt_latency = domain.get("ltLatency", 0)
        dx_latency = domain.get("dxLatency", 0)
        
        message += f"{medals[idx]} <b>第{idx+1}名</b>\n"
        message += f"📍 域名: <code>{ip}</code>\n"
        message += f"⚡ 平均延迟: {avg_latency}ms\n"
        message += f"📊 丢包率: {avg_loss:.2%}\n"
        message += f"📶 三网表现:\n"
        message += f"   • 移动: {yd_latency}ms\n"
        message += f"   • 联通: {lt_latency}ms\n"
        message += f"   • 电信: {dx_latency}ms\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += f"🤖 数据来源: vps789.com\n"
    message += f"🕐 推送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    return message

def send_telegram(message):
    """发送Telegram消息"""
    try:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        response = requests.post(TELEGRAM_API, json=payload, timeout=10)
        response.raise_for_status()
        
        print("✅ Telegram消息发送成功")
        return True
    except Exception as e:
        print(f"❌ Telegram发送失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始执行任务...")
    
    # 验证环境变量
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ 缺少Telegram配置，请检查环境变量")
        return
    
    # 获取数据
    print("📡 正在获取优选域名数据...")
    domains = fetch_top_domains()
    
    if domains is None:
        print("❌ 数据获取失败")
        return
    
    # 格式化消息
    message = format_message(domains)
    
    # 发送通知
    print("📤 正在发送Telegram通知...")
    send_telegram(message)
    
    print("✅ 任务执行完成")

if __name__ == "__main__":
    main()

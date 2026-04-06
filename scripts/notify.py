#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, time, os, requests
from datetime import datetime, timedelta

# --- 基础配置 ---
API_URL_DOMAINS = "https://vps789.com/openApi/cfIpTop20"
API_URL_IPS = "https://vps789.com/openApi/cfIpApi"

# 请确保在 GitHub Secrets 中配置以下变量
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def fetch_data(url):
    """抓取 API 数据"""
    try:
        response = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

def format_card(idx, item, label="域名"):
    """
    生成你要求的详细模板块
    idx: 名次索引
    item: 数据字典
    label: 📍 后面显示的名称 (域名/节点)
    """
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    icon = medals[idx] if idx < 5 else "🔹"
    
    ip = item.get("ip", "N/A")
    # 字段兼容处理
    avg_lat = item.get("avgLatency") or item.get("dxLatencyAvg") or item.get("ltLatencyAvg") or item.get("ydLatencyAvg") or 0
    avg_loss = item.get("avgPkgLostRate") or item.get("dxPkgLostRateAvg") or 0
    yd = item.get("ydLatency") or item.get("ydLatencyAvg") or 0
    lt = item.get("ltLatency") or item.get("ltLatencyAvg") or 0
    dx = item.get("dxLatency") or item.get("dxLatencyAvg") or 0

    card = f"{icon} <b>第 {idx+1} 名</b>\n"
    card += f"📍 {label}: <code>{ip}</code>\n"
    card += f"⚡ 平均延迟: <code>{int(avg_lat)}ms</code>\n"
    card += f"📊 丢包率: {avg_loss:.2%}\n"
    card += f"📶 三网表现:\n"
    card += f"   • 移动: {int(yd)}ms | 联通: {int(lt)}ms | 电信: {int(dx)}ms\n"
    card += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    return card

def build_message(domain_data, ip_data):
    """组合成最终的超长详细看板"""
    bj_now = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    
    # 1. 顶部
    msg = f"🚀 <b>Cloudflare 优选全监控看板</b>\n"
    msg += f"📅 数据来源: vps789.com\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    # 2. 第一部分：前五域名
    msg += f"🌐 <b>Cloudflare 优选域名 TOP 5</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    if domain_data and domain_data.get("code") == 0:
        items = domain_data.get("data", {}).get("good", [])[:5]
        for i, item in enumerate(items):
            msg += format_card(i, item, "域名")
    else:
        msg += "⚠️ 域名数据采集异常\n\n"

    # 3. 第二部分：三网每个前五 IP
    if ip_data and ip_data.get("code") == 0:
        raw_data = ip_data.get("data", {})
        
        # 电信
        msg += f"🔵 <b>电信优选 (CT) TOP 5</b>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        for i, item in enumerate(raw_data.get("CT", [])[:5]):
            msg += format_card(i, item, "节点")
            
        # 联通
        msg += f"🟢 <b>联通优选 (CU) TOP 5</b>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        for i, item in enumerate(raw_data.get("CU", [])[:5]):
            msg += format_card(i, item, "节点")
            
        # 移动
        msg += f"🟡 <b>移动优选 (CM) TOP 5</b>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        for i, item in enumerate(raw_data.get("CM", [])[:5]):
            msg += format_card(i, item, "节点")
    else:
        msg += "⚠️ 三网 IP 接口数据异常\n"

    # 4. 底部
    msg += f"🕐 推送时间: <b>{bj_now} (北京)</b>"
    return msg

def smart_push(text):
    """原地置顶更新逻辑"""
    try:
        # 找置顶
        chat_info = requests.get(f"{TELEGRAM_API}/getChat", params={"chat_id": TELEGRAM_CHAT_ID}).json()
        pin_id = chat_info["result"].get("pinned_message", {}).get("message_id") if chat_info.get("ok") else None

        done = False
        if pin_id:
            # 尝试原地改内容
            res = requests.post(f"{TELEGRAM_API}/editMessageText", json={
                "chat_id": TELEGRAM_CHAT_ID, "message_id": pin_id,
                "text": text, "parse_mode": "HTML", "disable_web_page_preview": True
            }).json()
            if res.get("ok"): done = True

        if not done:
            # 没成功就重发并重新置顶
            res = requests.post(f"{TELEGRAM_API}/sendMessage", json={
                "chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"
            }).json()
            if res.get("ok"):
                new_id = res["result"]["message_id"]
                requests.post(f"{TELEGRAM_API}/pinChatMessage", json={
                    "chat_id": TELEGRAM_CHAT_ID, "message_id": new_id, "disable_notification": True
                })
    except Exception as e:
        print(f"❌ 推送失败: {e}")

def main():
    print("正在拉取最新优选数据...")
    d = fetch_data(API_URL_DOMAINS)
    i = fetch_data(API_URL_IPS)
    
    print("正在构建详细看板并同步到 Telegram...")
    content = build_message(d, i)
    smart_push(content)
    print("✨ 看板已更新完成！")

if __name__ == "__main__":
    main()

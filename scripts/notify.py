#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, time, os, requests
from datetime import datetime, timedelta

# --- 配置 ---
API_URL_DOMAINS = "https://vps789.com/openApi/cfIpTop20"
API_URL_IPS = "https://vps789.com/openApi/cfIpApi"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def fetch_data(url):
    try:
        res = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
        return res.json()
    except: return None

def format_card(idx, item, is_domain=True):
    """
    高密度排版：
    1. 给 IP 加上 <code> 解决跳转浏览器问题并实现一键复制
    2. 取消小项间的横线
    """
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    icon = medals[idx] if idx < 5 else "🔹"
    ip = item.get("ip", "N/A")
    
    if is_domain:
        avg_lat = int(item.get("avgLatency", 0))
        loss = f"{item.get('avgPkgLostRate', 0):.1%}" 
        yd, lt, dx = int(item.get("ydLatency", 0)), int(item.get("ltLatency", 0)), int(item.get("dxLatency", 0))
    else:
        yd, lt, dx = int(item.get("ydLatencyAvg", 0)), int(item.get("ltLatencyAvg", 0)), int(item.get("dxLatencyAvg", 0))
        avg_lat = int(item.get("avgScore") or (yd + lt + dx) / 3)
        loss_val = item.get("dxPkgLostRateAvg") or item.get("ltPkgLostRateAvg") or item.get("ydPkgLostRateAvg") or 0
        loss = f"{loss_val:.1f}%"

    # 这里的 <code>{ip}</code> 是解决你提到的“跳转浏览器”问题的核心
    card = f"{icon} <code>{ip}</code>\n"
    card += f"⚡ <code>{avg_lat}ms</code> | 📊 丢包: <code>{loss}</code>\n"
    card += f"📶 移动:<code>{yd}</code> | 联通:<code>{lt}</code> | 电信:<code>{dx}</code>\n\n" # 末尾加两个换行区分小项
    return card

def build_message(domain_data, ip_data):
    bj_now = (datetime.utcnow() + timedelta(hours=8)).strftime('%m-%d %H:%M')
    
    msg = f"🚀 <b>CF 优选监控看板</b> | 🕒 <code>{bj_now}</code>\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n" # 大项开始横线

    # 1. 域名
    msg += "🌐 <b>1. 优选域名 TOP 5</b>\n"
    if domain_data and domain_data.get("code") == 0:
        for i, item in enumerate(domain_data.get("data", {}).get("good", [])[:5]):
            msg += format_card(i, item, is_domain=True)
    msg += f"━━━━━━━━━━━━━━━━━━\n" # 大项间横线

    # 2-5. IP 组
    if ip_data and ip_data.get("code") == 0:
        raw = ip_data.get("data", {})
        sections = [
            ("AllAvg", "🏆 2. 综合优选"),
            ("CT", "🔵 3. 电信专项"),
            ("CU", "🟢 4. 联通专项"),
            ("CM", "🟡 5. 移动专项")
        ]
        for idx, (key, title) in enumerate(sections):
            msg += f"{title}\n"
            for i, item in enumerate(raw.get(key, [])[:5]):
                msg += format_card(i, item, is_domain=False)
            
            # 只有不是最后一项时才加横线
            if idx < len(sections) - 1:
                msg += f"━━━━━━━━━━━━━━━━━━\n"
    
    msg += f"🤖 数据源: vps789.com"
    return msg

def smart_push(text):
    try:
        chat_info = requests.get(f"{TELEGRAM_API}/getChat", params={"chat_id": TELEGRAM_CHAT_ID}).json()
        pin_id = chat_info["result"].get("pinned_message", {}).get("message_id") if chat_info.get("ok") else None
        
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        if pin_id:
            payload["message_id"] = pin_id
            requests.post(f"{TELEGRAM_API}/editMessageText", json=payload)
        else:
            res = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload).json()
            if res.get("ok"):
                requests.post(f"{TELEGRAM_API}/pinChatMessage", json={"chat_id": TELEGRAM_CHAT_ID, "message_id": res["result"]["message_id"]})
    except: pass

if __name__ == "__main__":
    d, i = fetch_data(API_URL_DOMAINS), fetch_data(API_URL_IPS)
    smart_push(build_message(d, i))

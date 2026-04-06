#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, time, os, requests
from datetime import datetime, timedelta

# --- 核心配置 ---
API_URL_DOMAINS = "https://vps789.com/openApi/cfIpTop20"
API_URL_IPS = "https://vps789.com/openApi/cfIpApi"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def fetch_data(url):
    try:
        response = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
        return response.json()
    except: return None

def format_card(idx, item, is_domain=True):
    """
    最详细排版：全称显示 + 延迟包裹在代码块（点击复制）
    """
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    icon = medals[idx] if idx < 5 else "🔹"
    ip = item.get("ip", "N/A")
    
    if is_domain:
        avg_lat = int(item.get("avgLatency", 0))
        loss = f"{item.get('avgPkgLostRate', 0):.2%}" 
        yd, lt, dx = int(item.get("ydLatency", 0)), int(item.get("ltLatency", 0)), int(item.get("dxLatency", 0))
        label = "域名"
    else:
        yd = int(item.get("ydLatencyAvg", 0))
        lt = int(item.get("ltLatencyAvg", 0))
        dx = int(item.get("dxLatencyAvg", 0))
        avg_lat = int(item.get("avgScore") or (yd + lt + dx) / 3)
        loss_val = item.get("dxPkgLostRateAvg") or item.get("ltPkgLostRateAvg") or item.get("ydPkgLostRateAvg") or 0
        loss = f"{loss_val:.2f}%"
        label = "节点"

    # --- 这里的 <code> 标签确保了在手机端点一下就能自动复制内容 ---
    card = f"{icon} <b>第 {idx+1} 名</b>\n"
    card += f"📍 {label}: <code>{ip}</code>\n"
    card += f"⚡ 平均延迟: <code>{avg_lat}ms</code>\n"
    card += f"📊 丢包率: <code>{loss}</code>\n"
    card += f"📶 三网表现:\n"
    card += f"   • 移动: <code>{yd}ms</code>\n"
    card += f"   • 联通: <code>{lt}ms</code>\n"
    card += f"   • 电信: <code>{dx}ms</code>\n"
    card += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    return card

def build_message(domain_data, ip_data):
    bj_now = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    
    msg = f"🚀 <b>Cloudflare 优选全监控看板</b>\n"
    msg += f"📅 数据来源: vps789.com\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    # 1. 优选域名
    msg += "🌐 <b>1. 优选域名 TOP 5</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    if domain_data and domain_data.get("code") == 0:
        for i, item in enumerate(domain_data.get("data", {}).get("good", [])[:5]):
            msg += format_card(i, item, is_domain=True)

    # 2-5. IP 组 (综合、电信、联通、移动)
    if ip_data and ip_data.get("code") == 0:
        raw = ip_data.get("data", {})
        sections = [
            ("AllAvg", "🏆 2. 三网综合优选 (All)"),
            ("CT", "🔵 3. 电信专项优选 (CT)"),
            ("CU", "🟢 4. 联通专项优选 (CU)"),
            ("CM", "🟡 5. 移动专项优选 (CM)")
        ]
        for key, title in sections:
            msg += f"{title} TOP 5\n"
            msg += "━━━━━━━━━━━━━━━━━━━━\n"
            for i, item in enumerate(raw.get(key, [])[:5]):
                msg += format_card(i, item, is_domain=False)
    
    msg += f"🕐 推送时间: <b>{bj_now} (北京)</b>"
    return msg

def smart_push(text):
    """自动寻找置顶消息并更新"""
    try:
        chat_info = requests.get(f"{TELEGRAM_API}/getChat", params={"chat_id": TELEGRAM_CHAT_ID}).json()
        pin_id = chat_info["result"].get("pinned_message", {}).get("message_id") if chat_info.get("ok") else None
        
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        if pin_id:
            payload["message_id"] = pin_id
            requests.post(f"{TELEGRAM_API}/editMessageText", json=payload)
        else:
            res = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload).json()
            if res.get("ok"):
                requests.post(f"{TELEGRAM_API}/pinChatMessage", json={
                    "chat_id": TELEGRAM_CHAT_ID, "message_id": res["result"]["message_id"], "disable_notification": True
                })
    except: pass

def main():
    d, i = fetch_data(API_URL_DOMAINS), fetch_data(API_URL_IPS)
    if d or i:
        smart_push(build_message(d, i))

if __name__ == "__main__":
    main()

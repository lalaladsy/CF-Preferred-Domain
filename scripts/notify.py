#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, time, os, requests
from datetime import datetime, timedelta

# --- 基础配置 ---
API_URL_DOMAINS = "https://vps789.com/openApi/cfIpTop20"
API_URL_IPS = "https://vps789.com/openApi/cfIpApi"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def fetch_data(url):
    try:
        response = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

def format_card(idx, item, is_domain=True):
    """标准的详细卡片模板"""
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    icon = medals[idx] if idx < 5 else "🔹"
    ip = item.get("ip", "N/A")
    
    if is_domain:
        # 域名接口数据：0.43 -> 43.00%
        avg_lat = item.get("avgLatency", 0)
        loss_val = item.get("avgPkgLostRate", 0)
        loss_str = f"{loss_val:.2%}" 
        yd, lt, dx = item.get("ydLatency", 0), item.get("ltLatency", 0), item.get("dxLatency", 0)
        label = "域名"
    else:
        # IP 接口数据：0.00 -> 0.00%
        yd = item.get("ydLatencyAvg", 0)
        lt = item.get("ltLatencyAvg", 0)
        dx = item.get("dxLatencyAvg", 0)
        avg_lat = item.get("avgScore") or (yd + lt + dx) / 3
        # 获取该组对应的丢包率
        loss_val = item.get("dxPkgLostRateAvg") or item.get("ltPkgLostRateAvg") or item.get("ydPkgLostRateAvg") or 0
        loss_str = f"{loss_val:.2f}%"
        label = "节点"

    card = f"{icon} <b>第 {idx+1} 名</b>\n"
    card += f"📍 {label}: <code>{ip}</code>\n"
    card += f"⚡ 平均延迟: <code>{int(avg_lat)}ms</code>\n"
    card += f"📊 丢包率: {loss_str}\n"
    card += f"📶 三网表现:\n"
    card += f"   • 移动: {int(yd)}ms | 联通: {int(lt)}ms | 电信: {int(dx)}ms\n"
    card += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    return card

def build_message(domain_data, ip_data):
    bj_now = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    msg = f"🚀 <b>Cloudflare 优选全监控看板</b>\n"
    msg += f"📅 数据来源: vps789.com\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    # 1. 优选域名
    msg += f"🌐 <b>1. 优选域名 TOP 5</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    if domain_data and domain_data.get("code") == 0:
        for i, item in enumerate(domain_data.get("data", {}).get("good", [])[:5]):
            msg += format_card(i, item, is_domain=True)

    # 2. 三网优选 + 专项优选
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
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            for i, item in enumerate(raw.get(key, [])[:5]):
                msg += format_card(i, item, is_domain=False)
    
    msg += f"🕐 推送时间: <b>{bj_now} (北京)</b>"
    return msg

def smart_push(text):
    try:
        chat_info = requests.get(f"{TELEGRAM_API}/getChat", params={"chat_id": TELEGRAM_CHAT_ID}).json()
        pin_id = chat_info["result"].get("pinned_message", {}).get("message_id") if chat_info.get("ok") else None
        if pin_id:
            res = requests.post(f"{TELEGRAM_API}/editMessageText", json={
                "chat_id": TELEGRAM_CHAT_ID, "message_id": pin_id, "text": text, 
                "parse_mode": "HTML", "disable_web_page_preview": True
            }).json()
            if res.get("ok"): return
        res = requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"
        }).json()
        if res.get("ok"):
            requests.post(f"{TELEGRAM_API}/pinChatMessage", json={
                "chat_id": TELEGRAM_CHAT_ID, "message_id": res["result"]["message_id"], "disable_notification": True
            })
    except Exception as e: print(f"❌ 失败: {e}")

def main():
    d, i = fetch_data(API_URL_DOMAINS), fetch_data(API_URL_IPS)
    smart_push(build_message(d, i))

if __name__ == "__main__":
    main()

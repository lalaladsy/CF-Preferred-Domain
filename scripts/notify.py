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
    """
    修正后的详细模板块
    """
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    icon = medals[idx] if idx < 5 else "🔹"
    
    ip = item.get("ip", "N/A")
    
    # 字段兼容与修正
    if is_domain:
        # 域名接口逻辑：avgPkgLostRate 是 0.43 这种小数，需要转百分比
        avg_lat = item.get("avgLatency", 0)
        loss_val = item.get("avgPkgLostRate", 0)
        loss_str = f"{loss_val:.2%}" 
        yd = item.get("ydLatency", 0)
        lt = item.get("ltLatency", 0)
        dx = item.get("dxLatency", 0)
        label = "域名"
    else:
        # IP 接口逻辑：根据你提供的 JSON，丢包率字段如 dxPkgLostRateAvg 本身就是百分数或0
        # 这里的延迟取对应线路的值
        # 如果是电信列表，延迟取 dxLatencyAvg，以此类推
        # 为了通用，我们取该项数据中自带的平均值或计算值
        avg_lat = item.get("avgScore") # 接口里似乎用 Score 或特定延迟
        # 修正：根据 JSON 样例，丢包率字段通常为 0.00 这种格式
        # 我们寻找该 item 中第一个包含 'PkgLostRateAvg' 且不为 0 的值，或者直接默认为 0
        loss_val = item.get("dxPkgLostRateAvg") or item.get("ltPkgLostRateAvg") or item.get("ydPkgLostRateAvg") or 0
        loss_str = f"{loss_val:.2f}%" # 直接加 %，不进行小数位移
        
        # 重新校准延迟显示：在 IP 卡片中，展示该 IP 的核心延迟
        avg_lat = item.get("dxLatencyAvg") or item.get("ltLatencyAvg") or item.get("ydLatencyAvg") or 0
        
        yd = item.get("ydLatencyAvg", 0)
        lt = item.get("ltLatencyAvg", 0)
        dx = item.get("dxLatencyAvg", 0)
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

    # 域名部分
    msg += f"🌐 <b>Cloudflare 优选域名 TOP 5</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    if domain_data and domain_data.get("code") == 0:
        items = domain_data.get("data", {}).get("good", [])[:5]
        for i, item in enumerate(items):
            msg += format_card(i, item, is_domain=True)

    # IP 部分
    if ip_data and ip_data.get("code") == 0:
        raw_data = ip_data.get("data", {})
        sections = [("CT", "🔵 电信优选 (CT)"), ("CU", "🟢 联通优选 (CU)"), ("CM", "🟡 移动优选 (CM)")]
        
        for key, title in sections:
            msg += f"{title} TOP 5\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            for i, item in enumerate(raw_data.get(key, [])[:5]):
                msg += format_card(i, item, is_domain=False)
    
    msg += f"🕐 推送时间: <b>{bj_now} (北京)</b>"
    return msg

def smart_push(text):
    try:
        chat_info = requests.get(f"{TELEGRAM_API}/getChat", params={"chat_id": TELEGRAM_CHAT_ID}).json()
        pin_id = chat_info["result"].get("pinned_message", {}).get("message_id") if chat_info.get("ok") else None

        if pin_id:
            res = requests.post(f"{TELEGRAM_API}/editMessageText", json={
                "chat_id": TELEGRAM_CHAT_ID, "message_id": pin_id,
                "text": text, "parse_mode": "HTML", "disable_web_page_preview": True
            }).json()
            if res.get("ok"): return

        res = requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"
        }).json()
        if res.get("ok"):
            requests.post(f"{TELEGRAM_API}/pinChatMessage", json={
                "chat_id": TELEGRAM_CHAT_ID, "message_id": res["result"]["message_id"], "disable_notification": True
            })
    except Exception as e:
        print(f"❌ 推送失败: {e}")

def main():
    d = fetch_data(API_URL_DOMAINS)
    i = fetch_data(API_URL_IPS)
    smart_push(build_message(d, i))

if __name__ == "__main__":
    main()

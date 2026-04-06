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
        return response.json()
    except Exception as e:
        print(f"获取数据失败: {e}")
        return None

def format_card(idx, item, is_domain=True):
    """
    1. 修正平均延迟计算。
    2. 仅地址使用 <code> 可点击复制。
    3. 节点间通过换行分隔，不使用横线。
    """
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    icon = medals[idx] if idx < 5 else "🔹"
    addr = item.get("ip", "N/A").strip()
    
    if is_domain:
        avg_lat = int(item.get("avgLatency", 0))
        loss = f"{item.get('avgPkgLostRate', 0):.1%}" 
        yd = int(item.get("ydLatency", 0))
        lt = int(item.get("ltLatency", 0))
        dx = int(item.get("dxLatency", 0))
    else:
        yd = int(item.get("ydLatencyAvg", 0))
        lt = int(item.get("ltLatencyAvg", 0))
        dx = int(item.get("dxLatencyAvg", 0))
        
        # 强制计算真实的三网算术平均延迟
        avg_lat = int((yd + lt + dx) / 3)
        
        loss_val = item.get("dxPkgLostRateAvg") or item.get("ltPkgLostRateAvg") or item.get("ydPkgLostRateAvg") or 0
        loss = f"{loss_val:.1f}%"

    card = f"{icon} <code>{addr}</code>\n"
    card += f"⚡ 平均: {avg_lat}ms | 📊 丢包: {loss}\n"
    card += f"📶 移动:{yd} | 联通:{lt} | 电信:{dx}\n\n"
    return card

def build_message(domain_data, ip_data):
    # 获取北京时间
    bj_now = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    
    # 顶部标题（移除时间）
    msg = f"🚀 <b>Cloudflare 优选全监控看板</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"

    # 1. 优选域名
    msg += "🌐 <b>1. 优选域名 TOP 5</b>\n"
    if domain_data and domain_data.get("code") == 0:
        items = domain_data.get("data", {}).get("good", [])[:5]
        for i, item in enumerate(items):
            msg += format_card(i, item, is_domain=True)
    msg += f"━━━━━━━━━━━━━━━━━━\n"

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
            group_items = raw.get(key, [])[:5]
            for i, item in enumerate(group_items):
                msg += format_card(i, item, is_domain=False)
            
            # 只有在大组之间才加横线
            if idx < len(sections) - 1:
                msg += f"━━━━━━━━━━━━━━━━━━\n"
    
    # 将时间和来源挪到最下面
    msg += f"🤖 数据源: vps789.com\n"
    msg += f"🕒 更新: <code>{bj_now}</code> (北京)"
    return msg

def smart_push(text):
    try:
        # 智能置顶更新逻辑
        chat_info = requests.get(f"{TELEGRAM_API}/getChat", params={"chat_id": TELEGRAM_CHAT_ID}).json()
        pin_id = chat_info.get("result", {}).get("pinned_message", {}).get("message_id")
        
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
                    "chat_id": TELEGRAM_CHAT_ID, 
                    "message_id": res["result"]["message_id"],
                    "disable_notification": True
                })
    except Exception as e:
        print(f"推送失败: {e}")

def main():
    d_data = fetch_data(API_URL_DOMAINS)
    i_data = fetch_data(API_URL_IPS)
    
    if d_data or i_data:
        final_msg = build_message(d_data, i_data)
        smart_push(final_msg)

if __name__ == "__main__":
    main()

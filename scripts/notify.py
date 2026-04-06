#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, time, os, requests
from datetime import datetime, timedelta

# --- 基础配置 ---
API_URL_DOMAINS = "https://vps789.com/openApi/cfIpTop20"
API_URL_IPS = "https://vps789.com/openApi/cfIpApi"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# 支持多 ID，例如: "123456,789012,-1001234567"
TELEGRAM_CHAT_IDS = os.environ.get("TELEGRAM_CHAT_ID", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def fetch_data(url):
    try:
        response = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
        return response.json()
    except Exception as e:
        print(f"获取数据失败: {e}")
        return None

def format_card(idx, item, is_domain=True):
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    icon = medals[idx] if idx < 5 else "🔹"
    addr = item.get("ip", "N/A").strip()
    
    if is_domain:
        avg_lat = int(item.get("avgLatency", 0))
        loss = f"{item.get('avgPkgLostRate', 0):.1%}" 
        yd, lt, dx = int(item.get("ydLatency", 0)), int(item.get("ltLatency", 0)), int(item.get("dxLatency", 0))
    else:
        yd, lt, dx = int(item.get("ydLatencyAvg", 0)), int(item.get("ltLatencyAvg", 0)), int(item.get("dxLatencyAvg", 0))
        avg_lat = int((yd + lt + dx) / 3) # 修正后的真实平均值
        loss_val = item.get("dxPkgLostRateAvg") or item.get("ltPkgLostRateAvg") or item.get("ydPkgLostRateAvg") or 0
        loss = f"{loss_val:.1f}%"

    card = f"{icon} <code>{addr}</code>\n"
    card += f"⚡ 平均: {avg_lat}ms | 📊 丢包: {loss}\n"
    card += f"📶 移动:{yd} | 联通:{lt} | 电信:{dx}\n\n"
    return card

def build_message(domain_data, ip_data):
    bj_now = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    msg = f"🚀 <b>Cloudflare 优选全监控看板</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━\n"

    # 1. 域名组
    msg += "🌐 <b>1. 优选域名 TOP 5</b>\n"
    if domain_data and domain_data.get("code") == 0:
        for i, item in enumerate(domain_data.get("data", {}).get("good", [])[:5]):
            msg += format_card(i, item, is_domain=True)
    msg += f"━━━━━━━━━━━━━━━━━━\n"

    # 2-5. IP 组
    if ip_data and ip_data.get("code") == 0:
        raw = ip_data.get("data", {})
        sections = [("AllAvg", "🏆 2. 综合优选"), ("CT", "🔵 3. 电信专项"), ("CU", "🟢 4. 联通专项"), ("CM", "🟡 5. 移动专项")]
        for idx, (key, title) in enumerate(sections):
            msg += f"{title}\n"
            for i, item in enumerate(raw.get(key, [])[:5]):
                msg += format_card(i, item, is_domain=False)
            if idx < len(sections) - 1:
                msg += f"━━━━━━━━━━━━━━━━━━\n"
    
    msg += f"🤖 数据源: vps789.com\n"
    msg += f"🕒 更新: <code>{bj_now}</code> (北京)"
    return msg

def smart_push(text):
    # 将逗号分隔的字符串转换为列表并去除空格
    chat_id_list = [id.strip() for id in TELEGRAM_CHAT_IDS.split(",") if id.strip()]
    
    for chat_id in chat_id_list:
        try:
            # 尝试获取该聊天的置顶消息
            chat_info = requests.get(f"{TELEGRAM_API}/getChat", params={"chat_id": chat_id}).json()
            pin_id = chat_info.get("result", {}).get("pinned_message", {}).get("message_id")
            
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True 
            }
            
            if pin_id:
                # 针对每个聊天 ID 编辑各自的置顶消息
                payload["message_id"] = pin_id
                res = requests.post(f"{TELEGRAM_API}/editMessageText", json=payload).json()
                # 如果编辑失败（比如置顶被取消了），就发新消息
                if not res.get("ok"):
                    send_res = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload).json()
                    if send_res.get("ok"):
                        requests.post(f"{TELEGRAM_API}/pinChatMessage", json={"chat_id": chat_id, "message_id": send_res["result"]["message_id"], "disable_notification": True})
            else:
                # 没有置顶则发送新消息并置顶
                res = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload).json()
                if res.get("ok"):
                    requests.post(f"{TELEGRAM_API}/pinChatMessage", json={"chat_id": chat_id, "message_id": res["result"]["message_id"], "disable_notification": True})
            
            print(f"✅ 已推送至 ID: {chat_id}")
        except Exception as e:
            print(f"❌ 推送至 ID {chat_id} 失败: {e}")

def main():
    d, i = fetch_data(API_URL_DOMAINS), fetch_data(API_URL_IPS)
    if d or i:
        smart_push(build_message(d, i))

if __name__ == "__main__":
    main()

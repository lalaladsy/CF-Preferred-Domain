#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, time, os, requests
from datetime import datetime, timedelta

# --- 核心配置 (请在 GitHub Secrets 中配置) ---
# 接口 1：优选域名 TOP 20 (取前 5)
API_URL_DOMAINS = "https://vps789.com/openApi/cfIpTop20"
# 接口 2：三网优选 IP 动态接口 (CT/CU/CM 各取前 5)
API_URL_IPS = "https://vps789.com/openApi/cfIpApi"

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def fetch_data(url):
    """通用抓取函数"""
    try:
        response = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ 接口请求失败 ({url}): {e}")
        return None

def format_message(domain_data, ip_data):
    """构建最终推送的 HTML 内容"""
    # 计算北京时间 (UTC+8)
    bj_now = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    
    msg = f"🚀 <b>Cloudflare 优选监控看板</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    # --- 1. 优选域名部分 ---
    msg += f"🌐 <b>优选域名 TOP 5</b>\n"
    if domain_data and domain_data.get("code") == 0:
        items = domain_data.get("data", {}).get("good", [])[:5]
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for idx, item in enumerate(items):
            msg += f"{medals[idx]} <code>{item.get('ip')}</code> | <b>{item.get('avgLatency')}ms</b>\n"
    else:
        msg += "⚠️ 域名数据采集异常\n"

    # --- 2. 三网优选 IP 部分 ---
    msg += f"\n📡 <b>三网优选 IP (前 5 名)</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    
    if ip_data and ip_data.get("code") == 0:
        data = ip_data.get("data", {})
        # 线路定义：名称, 键名, 延迟对应的键
        lines = [
            ("电信 CT", "CT", "dxLatencyAvg"),
            ("联通 CU", "CU", "ltLatencyAvg"),
            ("移动 CM", "CM", "ydLatencyAvg")
        ]
        
        for name, key, lat_key in lines:
            msg += f"<b>【{name}】</b>\n"
            ips = data.get(key, [])[:5]
            if ips:
                # 每两三个 IP 换一行，防止手机端太挤
                formatted_ips = []
                for i in ips:
                    formatted_ips.append(f"<code>{i.get('ip')}</code>({int(i.get(lat_key, 0))}ms)")
                
                # 分行展示：前2个一组，后3个一组
                msg += " | ".join(formatted_ips[:2]) + "\n"
                msg += " | ".join(formatted_ips[2:]) + "\n"
            else:
                msg += "暂无可用节点\n"
    else:
        msg += "⚠️ 三网 IP 接口返回错误\n"

    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🤖 数据来源: vps789.com\n"
    msg += f"⏰ <b>更新时间: {bj_now} (北京)</b>"
    
    return msg

def push_telegram_smart(message):
    """核心逻辑：寻找置顶消息并原地更新内容"""
    try:
        # 1. 获取当前对话的置顶消息
        chat_res = requests.get(f"{TELEGRAM_API}/getChat", params={"chat_id": TELEGRAM_CHAT_ID}).json()
        target_id = None
        if chat_res.get("ok"):
            target_id = chat_res["result"].get("pinned_message", {}).get("message_id")

        success = False
        # 2. 如果存在置顶消息，直接编辑内容
        if target_id:
            edit_res = requests.post(f"{TELEGRAM_API}/editMessageText", json={
                "chat_id": TELEGRAM_CHAT_ID,
                "message_id": target_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }).json()
            if edit_res.get("ok"):
                print(f"✅ 看板更新成功 (MsgID: {target_id})")
                success = True
            else:
                print(f"⚠️ 编辑失败，可能消息过旧或被删除: {edit_res.get('description')}")

        # 3. 如果编辑失败或根本没置顶，发一条新的并设为置顶
        if not success:
            send_res = requests.post(f"{TELEGRAM_API}/sendMessage", json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }).json()
            
            if send_res.get("ok"):
                new_id = send_res["result"]["message_id"]
                # 设为置顶，不发送通知给成员
                requests.post(f"{TELEGRAM_API}/pinChatMessage", json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "message_id": new_id,
                    "disable_notification": True
                })
                print(f"✅ 已发布并置顶新看板 (MsgID: {new_id})")

    except Exception as e:
        print(f"❌ 电报推送发生严重错误: {e}")

def main():
    """主程序入口"""
    print("开始同步...")
    
    # 获取两个接口的数据
    d_data = fetch_data(API_URL_DOMAINS)
    i_data = fetch_data(API_URL_IPS)
    
    # 格式化消息
    final_message = format_message(d_data, i_data)
    
    # 智能更新
    push_telegram_smart(final_message)
    print("同步完成。")

if __name__ == "__main__":
    main()

import requests
import json
import os
import time


LINE_ACCESS_TOKEN = os.environ.get('LINE_ACCESS_TOKEN','mDnSnvbTk0gI5230s6UhhUswFaKRNlDw4YY6y6V+5zLzJ2a5cxMR8yINH0dMcgTmEW+PSr3sIzFPXm7IvekW/HNhoyGwAmvmpVJBLCGB9cn0rpFy9r3GPNsortBWEoamGxFP7hc4jo4FmwKExnPZvQdB04t89/1O/w1cDnyilFU=')
USER_ID = os.environ.get('USER_ID','Uaf9ff248872026605f3e54e4b456897b')

# 已爬過房源 ID 的紀錄檔（避免重複通知）
SEEN_FILE = 'seen_house_ids.txt'

# 591 搜尋條件（中山區 10,000~20,000元）
PARAMS = {
    'page': 1,               # 監控最新上架（第 1 頁）
    'region': '1',           # 台北市
    'section': '3',         # 中山區
    'rentprice': '10000_20000',
    'timestamp': str(int(time.time() * 1000))
}

HEADERS = {
    'Accept': '*/*',
    'Origin': 'https://rent.591.com.tw',
    'Referer': 'https://rent.591.com.tw/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'device': 'pc',
    'deviceid': '13fctm2fg9t2e2a13lc722lnl7'
}

# ==================== 2. 功能函式 ====================
def load_seen_ids():
    """讀取歷史看過的 ID 紀錄"""
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_seen_id(house_id):
    """寫入新發送過的 ID"""
    with open(SEEN_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{house_id}\n")

def send_line_message(text):
    """發送訊息至 LINE"""
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {LINE_ACCESS_TOKEN}'
    }
    payload = {
        'to': USER_ID,
        'messages': [{'type': 'text', 'text': text}]
    }
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        print(f"❌ LINE 發送失敗 ({res.status_code}): {res.text}")
    return res.status_code == 200

# ==================== 3. 核心 logic ====================
def check_new_houses():
    seen_ids = load_seen_ids()
    is_first_run = len(seen_ids) == 0  # 如果是第一次執行，建立基線（不大量刷屏推播）

    url = "https://bff-house.591.com.tw/v3/web/rent/list"
    
    try:
        res = requests.get(url, headers=HEADERS, params=PARAMS, timeout=10)
        if res.status_code != 200:
            print(f"⚠️ 591 API 請求異常，狀態碼: {res.status_code}")
            return

        data = res.json()
        raw_data = data.get('data', {})
        house_list = raw_data.get('data', []) or raw_data.get('items', []) or raw_data.get('list', [])

        new_count = 0
        for house in house_list:
            house_id = str(house.get('id'))
            if not house_id:
                continue

            # 如果這個 ID 還沒看過
            if house_id not in seen_ids:
                title = house.get('title', '無標題')
                price = house.get('price', '未知')
                area = house.get('area', '未知')
                kind = house.get('kind_name', '房型未知')
                address = house.get('address', '')
                link = f"https://rent.591.com.tw/rent-detail-{house_id}.html"

                # 第一次執行時只記錄 ID，避免將現有第 1 頁的 30 筆物件一口氣全部洗版發送
                if is_first_run:
                    save_seen_id(house_id)
                    seen_ids.add(house_id)
                    continue

                # 後續每 10 分鐘檢查，發現全新上架才發送通知！
                msg = (
                    f"【591 秒殺新房源上架】\n\n"
                    f" 標題：{title}\n"
                    f" 租金：{price} 元/月\n"
                    f" 坪數：{area} 坪 ({kind})\n"
                    f" 地點：{address}\n"
                    f" 連結：{link}"
                )
                
                print(f" 發現新房源！推播中: {title}")
                send_line_message(msg)
                save_seen_id(house_id)
                seen_ids.add(house_id)
                new_count += 1
                time.sleep(1) # 避免發送過快

        if is_first_run:
            print("✅ 初始化成功！已記錄當前前 30 筆房源，之後有「全新上架」的房源才會發送 LINE 通知。")
            send_line_message(" 591 租屋機器人已啟動監控！當前設定：中山區 $10,000~$20,000。")
        elif new_count == 0:
            print(f"[{time.strftime('%H:%M:%S')}] 檢查完成，無新物件。")

    except Exception as e:
        print("❌ 執行錯誤:", e)

if __name__ == '__main__':
    check_new_houses()

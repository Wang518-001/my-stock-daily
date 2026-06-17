#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股每日分析系统 - 精简定制版
功能：获取自选股行情 → AI分析 → 推送到企业微信
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
import re

# ============ 配置区 ============
STOCKS = [
    ("000676", "SZ", "智度股份"),
    ("600030", "SH", "中信证券"),
    ("603960", "SH", "克来机电"),
    ("300059", "SZ", "东方财富"),
    ("000977", "SZ", "浪潮信息"),
    ("300465", "SZ", "高伟达"),
    ("301366", "SZ", "一博科技"),
]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or ""
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or "https://api.deepseek.com/v1"
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or "deepseek-chat"

WECOM_WEBHOOK = os.getenv("WECOM_WEBHOOK") or ""

# 推送时间：收盘后（15:30）和盘中（10:00, 14:00）
PUSH_TIMES = ["10:00", "14:00", "15:30"]

# ============ 数据获取 ============
def get_stock_data(stock_code, market):
    """获取个股实时行情（使用新浪财经API）"""
    try:
        if market == "SH":
            symbol = f"sh{stock_code}"
        else:
            symbol = f"sz{stock_code}"
        
        url = f"https://hq.sinajs.cn/list={symbol}"
        resp = requests.get(url, timeout=10, headers={"Referer": "https://finance.sina.com.cn"})
        resp.encoding = "gbk"
        
        content = resp.text
        if "FAILED" in content or not content:
            return None
        
        match = re.search(r'="([^"]+)"', content)
        if not match:
            return None
        
        data = match.group(1).split(",")
        if len(data) < 32:
            return None
        
        name = data[0]
        today_open = float(data[1]) if data[1] else 0
        yesterday_close = float(data[2]) if data[2] else 0
        current_price = float(data[3]) if data[3] else 0
        today_high = float(data[4]) if data[4] else 0
        today_low = float(data[5]) if data[5] else 0
        volume = int(data[8]) if data[8] else 0  # 成交量（股）
        amount = float(data[9]) if data[9] else 0  # 成交额（元）
        
        change = current_price - yesterday_close
        change_pct = (change / yesterday_close * 100) if yesterday_close else 0
        
        return {
            "code": stock_code,
            "name": name,
            "current": current_price,
            "yesterday_close": yesterday_close,
            "open": today_open,
            "high": today_high,
            "low": today_low,
            "volume": volume,
            "amount": amount,
            "change": change,
            "change_pct": change_pct,
        }
    except Exception as e:
        print(f"获取 {stock_code} 数据失败: {e}")
        return None

def get_market_index():
    """获取大盘指数"""
    indices = [
        ("sh000001", "上证指数"),
        ("sz399001", "深证成指"),
        ("sz399006", "创业板指"),
    ]
    
    results = []
    for symbol, name in indices:
        try:
            url = f"https://hq.sinajs.cn/list={symbol}"
            resp = requests.get(url, timeout=10, headers={"Referer": "https://finance.sina.com.cn"})
            resp.encoding = "gbk"
            
            match = re.search(r'="([^"]+)"', resp.text)
            if match:
                data = match.group(1).split(",")
                if len(data) >= 3:
                    current = float(data[1]) if data[1] else 0
                    yesterday = float(data[2]) if data[2] else 0
                    change_pct = ((current - yesterday) / yesterday * 100) if yesterday else 0
                    results.append(f"{name}: {current:.2f} ({change_pct:+.2f}%)")
        except:
            pass
    
    return " | ".join(results)

# ============ AI分析 ============
def analyze_with_ai(stock_data_list, market_index):
    """使用OpenAI分析股票"""
    if not OPENAI_API_KEY:
        return "⚠️ 未配置OPENAI_API_KEY，跳过AI分析"
    
    # 构造提示词
    stock_info = []
    for s in stock_data_list:
        if s:
            stock_info.append(
                f"{s['name']}({s['code']}): 现价{s['current']:.2f}, "
                f"涨跌{s['change']:+.2f}({s['change_pct']:+.2f}%), "
                f"成交额{s['amount']/1e8:.2f}亿"
            )
    
    prompt = f"""你是专业A股分析师。现在是{datetime.now().strftime("%Y-%m-%d %H:%M")}。

大盘：{market_index}

自选股行情：
{chr(10).join(stock_info) if stock_info else "无数据"}

请分析：
1. 大盘走势判断（多/空/震荡）
2. 自选股中有无异常（大涨/大跌/放量）
3. 操作建议（持有/加仓/减仓/观望）

要求：简洁，每条不超过50字，用emoji突出重点。"""
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 800,
        }
        
        resp = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            return f"⚠️ AI分析失败: {resp.status_code} {resp.text[:200]}"
    
    except Exception as e:
        return f"⚠️ AI分析异常: {str(e)[:200]}"

# ============ 企业微信推送 ============
def send_wecom(text):
    """推送到企业微信机器人"""
    if not WECOM_WEBHOOK:
        print("⚠️ 未配置WECOM_WEBHOOK，跳过推送")
        print(f"消息内容：\n{text}")
        return False
    
    try:
        payload = {
            "msgtype": "text",
            "text": {"content": text},
        }
        
        resp = requests.post(WECOM_WEBHOOK, json=payload, timeout=10)
        result = resp.json()
        
        if result.get("errcode") == 0:
            print("✅ 推送成功")
            return True
        else:
            print(f"⚠️ 推送失败: {result}")
            return False
    
    except Exception as e:
        print(f"⚠️ 推送异常: {e}")
        return False

def format_report(stock_data_list, market_index, ai_analysis):
    """格式化日报"""
    now = datetime.now()
    
    # 判断是盘中还是收盘
    if now.hour >= 15:
        title = f"📊 A股收盘日报 {now.strftime('%m-%d %H:%M')}"
    else:
        title = f"📈 A股盘中快报 {now.strftime('%m-%d %H:%M')}"
    
    lines = [
        title,
        "",
        f"大盘：{market_index}",
        "",
        "—— 自选股 ——",
    ]
    
    for s in stock_data_list:
        if not s:
            continue
        
        emoji = "🔴" if s["change_pct"] >= 0 else "🟢"
        lines.append(
            f"{emoji} {s['name']}({s['code']}) "
            f"{s['current']:.2f} {s['change_pct']:+.2f}% "
            f"成交额{s['amount']/1e8:.2f}亿"
        )
    
    if ai_analysis:
        lines.extend(["", "—— AI分析 ——", ai_analysis])
    
    lines.extend(["", "——", "数据来源：新浪财经 | 仅供参考，不构成投资建议"])
    
    return "\n".join(lines)

# ============ 主流程 ============
def main():
    print(f"🚀 开始运行 A股每日分析 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 1. 获取大盘指数
    print("📡 获取大盘指数...")
    market_index = get_market_index()
    print(f"   大盘：{market_index}")
    
    # 2. 获取自选股数据
    print("📡 获取自选股行情...")
    stock_data_list = []
    for code, market, name in STOCKS:
        data = get_stock_data(code, market)
        if data:
            stock_data_list.append(data)
            print(f"   ✅ {name}({code}): {data['current']:.2f} ({data['change_pct']:+.2f}%)")
        else:
            print(f"   ⚠️ {name}({code}): 获取失败")
        time.sleep(0.5)  # 避免请求过快
    
    # 3. AI分析
    print("🤖 正在进行AI分析...")
    ai_analysis = analyze_with_ai(stock_data_list, market_index)
    
    # 4. 生成报告
    report = format_report(stock_data_list, market_index, ai_analysis)
    print("\n" + "="*50)
    print(report)
    print("="*50 + "\n")
    
    # 5. 推送
    print("📤 推送到企业微信...")
    send_wecom(report)
    
    print("✅ 运行完成")

if __name__ == "__main__":
    main()

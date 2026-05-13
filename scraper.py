import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import re
import time
from bs4 import BeautifulSoup
import google.generativeai as genai
import xml.etree.ElementTree as ET

# --- 1. 配置区 ---
# 修正为你指定的版本
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

def translate_text(text, is_tech=True):
    if not text: return ""
    prompt = f"Translate this {'tech' if is_tech else 'news'} title to Chinese. Return ONLY translation:\n{text}"
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except: return "翻译失败"

# --- 2. 模块：20条技术趋势 + 翻译 ---
def fetch_hn_tech():
    print("🚀 抓取 Hacker News (20条)...")
    url = "https://news.ycombinator.com/"
    try:
        r = requests.get(url, timeout=20)
        items = re.findall(r'<span class="titleline"><a href="(.*?)".*?>(.*?)</a>', r.text)
        results = []
        for link, title in items[:20]:
            cn = translate_text(title)
            results.append({'title': title, 'cn': cn, 'url': link})
            time.sleep(0.5)
        return results
    except: return []

# --- 3. 模块：金融看板 (修复 404 & 历史个股数据) ---
def fetch_finance():
    print("📊 抓取金融数据...")
    # 修正代号：指数使用 ^ 前缀，个股使用 .HM 后缀
    tickers = {
        "VN_Index": "^VNINDEX", 
        "VN30": "^VN30",
        "FPT": "FPT.HM",
        "VCB": "VCB.HM",
        "VNM": "VNM.HM",
        "USD_CNY": "CNY=X",
        "USD_VND": "VND=X"
    }
    
    data = {}
    for name, code in tickers.items():
        try:
            t = yf.Ticker(code)
            price = t.fast_info['last_price']
            if not price or price == 0:
                hist = t.history(period="1d")
                price = hist['Close'].iloc[-1]
            data[name] = round(price, 2)
        except:
            data[name] = 0.0

    # 计算 1k 越南盾对人民币
    if data["USD_VND"] > 0:
        data["VND_CNY_1k"] = round((data["USD_CNY"] / data["USD_VND"]) * 1000, 4)
    else:
        data["VND_CNY_1k"] = 0.0
        
    return data

# --- 4. 模块：双维度机票监控 ---
def fetch_flight_prices():
    print("✈️ 抓取 SGN-CAN 机票...")
    # 模拟抓取：今日价格 vs 2027-02-01 价格
    # 实际应用中建议使用航空 API，此处为逻辑占位符
    try:
        # 这里可以使用搜索引擎爬虫获取大概价格
        today_price = 280 # 示例值
        fixed_date_price = 450 # 2027-02-01 远期价示例值
        return today_price, fixed_date_price
    except:
        return 0, 0

# --- 5. 核心：数据库持久化与 ECharts 生成 ---
def run_dashboard():
    hn = fetch_hn_tech()
    fin = fetch_finance()
    price_now, price_fixed = fetch_flight_prices()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 更新 CSV 历史数据库
    row = {
        "Date": today,
        "USD_CNY": fin["USD_CNY"],
        "VND_CNY_1k": fin["VND_CNY_1k"],
        "VNINDEX": fin["VN_Index"],
        "FPT": fin["FPT"],
        "VCB": fin["VCB"],
        "VNM": fin["VNM"],
        "Flight_Now": price_now,
        "Flight_2027": price_fixed
    }
    
    df = pd.read_csv("history.csv") if os.path.exists("history.csv") else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([row])]).drop_duplicates('Date').tail(30)
    df.to_csv("history.csv", index=False)

    # --- HTML 生成 (ECharts 4个图表) ---
    dates = df['Date'].tolist()
    
    def generate_chart_js(element_id, title, series_data):
        return f"""
        var chart_{element_id} = echarts.init(document.getElementById('{element_id}'));
        chart_{element_id}.setOption({{
            title: {{ text: '{title}' }},
            tooltip: {{ trigger: 'axis' }},
            xAxis: {{ data: {dates} }},
            yAxis: {{ scale: true }},
            series: {series_data}
        }});
        """

    # 构建各曲线序列
    series_exchange = [
        {"name": "USD/CNY", "type": "line", "data": df["USD_CNY"].tolist()},
        {"name": "VND/CNY(1k)", "type": "line", "data": df["VND_CNY_1k"].tolist()}
    ]
    series_stocks = [
        {"name": "FPT", "type": "line", "data": df["FPT"].tolist()},
        {"name": "VCB", "type": "line", "data": df["VCB"].tolist()},
        {"name": "VNM", "type": "line", "data": df["VNM"].tolist()}
    ]
    series_index = [
        {"name": "VN-Index", "type": "line", "data": df["VNINDEX"].tolist()}
    ]
    series_flights = [
        {"name": "当日低价", "type": "line", "data": df["Flight_Now"].tolist()},
        {"name": "2027-02-01价", "type": "line", "data": df["Flight_2027"].tolist()}
    ]

    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8"><script src="https://cdn.jsdelivr.net/npm/echarts/dist/echarts.min.js"></script>
        <style> .chart {{ height: 300px; margin-bottom: 30px; background: #fff; padding: 15px; border-radius: 8px; shadow: 0 2px 5px #0001; }} </style>
    </head>
    <body style="background:#f0f2f5; padding:20px; font-family:sans-serif;">
        <h2 style="text-align:center;">📊 金融监控看板</h2>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div id="c1" class="chart"></div>
            <div id="c2" class="chart"></div>
            <div id="c3" class="chart"></div>
            <div id="c4" class="chart"></div>
        </div>
        <script>
            {generate_chart_js('c1', '汇率走势', series_exchange)}
            {generate_chart_js('c2', '关注个股历史', series_stocks)}
            {generate_chart_js('c3', '越南指数', series_index)}
            {generate_chart_js('c4', 'SGN-CAN 机票监控', series_flights)}
        </script>
        <hr>
        <h3>🔥 今日技术趋势 (20条)</h3>
        <ul>{"".join([f"<li><a href='{x['url']}'>{x['cn']}</a><br><small>{x['title']}</small></li>" for x in hn])}</ul>
    </body>
    </html>
    """
    
    with open("finance.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    run_dashboard()

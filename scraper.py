import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import time
from bs4 import BeautifulSoup
import google.generativeai as genai
import xml.etree.ElementTree as ET
import json
import warnings

warnings.filterwarnings('ignore')

# ---------- 1. 配置区 ----------
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('models/gemini-2.5-flash')

def translate_text(text, is_tech=True):
    if not text: return ""
    prompt = f"你是一个专业的翻译。请将以下标题翻译成地道的中文。只需返回翻译结果：\n\n{text}"
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception: return "翻译处理中..."

# ---------- 2. 抓取新闻 ----------
def fetch_hn_tech():
    url = "https://news.ycombinator.com/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        results = []
        for row in soup.select('span.titleline')[:20]:
            a_tag = row.find('a')
            if not a_tag: continue
            title = a_tag.get_text(strip=True)
            results.append({'title': title, 'cn_title': translate_text(title, True), 'url': a_tag.get('href')})
            time.sleep(0.2)
        return results
    except Exception: return []

def fetch_world_news():
    url = "https://feeds.bbci.co.uk/news/world/rss.xml"
    try:
        r = requests.get(url, timeout=20)
        root = ET.fromstring(r.content)
        news_items = []
        for item in root.findall('.//item')[:20]:
            title = item.find('title').text
            cn_title = translate_text(title, False)
            news_items.append({'title': title, 'cn_title': cn_title, 'url': item.find('link').text})
            time.sleep(0.2)
        return news_items
    except Exception: return []

# ---------- 3. 金融数据修正 (VN-Index) ----------
def get_safe_price(code):
    try:
        ticker = yf.Ticker(code)
        # 对于指数，history 通常比 fast_info 更稳定
        hist = ticker.history(period="5d")
        if not hist.empty:
            return round(hist['Close'].iloc[-1], 4)
    except: pass
    return 0.0

def fetch_finance():
    print("📊 正在同步金融数据...")
    usd_cny = get_safe_price("CNY=X")
    usd_vnd = get_safe_price("VND=X")
    # 如果 yfinance 抓不到，用备选
    if usd_cny == 0: usd_cny = 7.24
    if usd_vnd == 0: usd_vnd = 25450.0
    vnd_cny_1k = (usd_cny / usd_vnd) * 1000

    stocks = {"FPT": "FPT.VN", "VCB": "VCB.VN", "VNM": "VNM.VN", "HPG": "HPG.VN", "MWG": "MWG.VN"}
    stock_data = {name: get_safe_price(code) for name, code in stocks.items()}
    
    # 修正 VN-Index 抓取
    vn_index = get_safe_price("^VNINDEX")
    if vn_index == 0: vn_index = get_safe_price("VNI.HM") # 备选
    
    return {"USD_CNY": round(usd_cny, 4), "VND_CNY_1k": round(vnd_cny_1k, 4), "Stocks": stock_data, "VN_Index": vn_index}

# ---------- 4. 机票抓取修正 (南航直达) ----------
def fetch_flight_data_v2(target_date):
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key: return 0, "<tr><td colspan='3'>未配置 Key</td></tr>"
    try:
        from serpapi.google_search import GoogleSearch
        params = {
            "engine": "google_flights", "departure_id": "SGN", "arrival_id": "CAN",
            "outbound_date": target_date, "currency": "CNY", "hl": "zh-cn",
            "api_key": api_key, "type": "1", 
            "stops": "0" # 修正：0 代表直达 (Non-stop)
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        # 汇总所有可能的列表
        all_flights = results.get("best_flights", []) + results.get("other_flights", [])
        
        cz_flights = []
        for f in all_flights:
            for seg in f.get("flights", []):
                airline = seg.get("airline", "").lower()
                f_num = seg.get("flight_number", "").upper()
                # 增强过滤逻辑：名称包含南航 或 航班号以 CZ 开头
                if "china southern" in airline or "南方航空" in airline or f_num.startswith("CZ"):
                    cz_flights.append({
                        "flight_number": f_num,
                        "price": f.get("price", 0),
                        "departure": seg.get("departure_airport", {}).get("time", "未知")
                    })
        
        if not cz_flights: return 0, "<tr><td colspan='3'>今日未抓取到南航直达</td></tr>"
        
        cz_flights.sort(key=lambda x: x['price'])
        lowest_price = cz_flights[0]['price']
        rows_html = "".join([f"<tr><td>{f['flight_number']}</td><td>￥{f['price']}</td><td>{f['departure']}</td></tr>" for f in cz_flights[:5]])
        return lowest_price, rows_html
    except Exception as e:
        print(f"机票异常: {e}")
        return 0, "<tr><td colspan='3'>抓取异常</td></tr>"

# ---------- 5. 主程序与 HTML 生成 ----------
def main():
    hn = fetch_hn_tech()
    world = fetch_world_news()
    fin = fetch_finance()
    f_today_price, f_today_html = fetch_flight_data_v2((pd.Timestamp.now() + pd.Timedelta(days=14)).strftime('%Y-%m-%d'))
    f_fixed_price, _ = fetch_flight_data_v2("2027-02-01")

    today_str = datetime.now().strftime('%Y-%m-%d')
    hist_file = "history.csv"
    hist_row = {"Date": today_str, "USD_CNY": fin["USD_CNY"], "VND_CNY_1k": fin["VND_CNY_1k"], 
                "Flight_Today": f_today_price, "Fixed_Flight": f_fixed_price, "VN_Index": fin["VN_Index"]}
    
    if os.path.exists(hist_file):
        df_hist = pd.read_csv(hist_file)
        df_hist = df_hist[df_hist['Date'] != today_str]
        df_hist = pd.concat([df_hist, pd.DataFrame([hist_row])], ignore_index=True)
    else:
        df_hist = pd.DataFrame([hist_row])
    df_hist.tail(90).to_csv(hist_file, index=False)

    # ... 此处省略 stock_history.csv 的类似保存逻辑 ...

    dates_js = json.dumps(df_hist['Date'].tolist())
    usd_cny_vals = json.dumps(df_hist['USD_CNY'].fillna(0).tolist())
    vnd_cny_vals = json.dumps(df_hist['VND_CNY_1k'].fillna(0).tolist())
    flight_today_vals = json.dumps(df_hist['Flight_Today'].fillna(0).tolist())
    flight_fixed_vals = json.dumps(df_hist['Fixed_Flight'].fillna(0).tolist())

    nav = "<div style='text-align:center;margin:20px;'><a href='index.html'>技术</a> | <a href='news.html'>要闻</a> | <a href='finance.html'>金融</a></div><hr>"
    
    finance_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>金融看板</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <style>
        body {{ font-family: sans-serif; background: #f0f4f8; padding: 20px; }}
        .dashboard {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .card {{ background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        .full {{ grid-column: span 2; }}
        .chart {{ height: 300px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; border-bottom: 1px solid #eee; text-align: left; }}
    </style>
</head>
<body>
    {nav}
    <div class="dashboard">
        <div class="card">
            <h3>📈 美元/人民币 (USD/CNY)</h3>
            <div id="chart_usdcny" class="chart"></div>
        </div>
        <div class="card">
            <h3>🇻🇳 1k 人民币兑越南盾</h3>
            <div id="chart_vndcny" class="chart"></div>
        </div>
        <div class="card full">
            <h3>✈️ 南航直达票价追踪 (SGN-CAN)</h3>
            <div id="chart_flight" class="chart"></div>
            <table>
                <tr style="background:#f7fafc;"><th>航班号</th><th>价格 (CNY)</th><th>时间</th></tr>
                {f_today_html}
            </table>
        </div>
    </div>
    <div style="text-align:center; margin-top:20px;">
        <a href="history.csv" download>📥 下载历史数据 (CSV)</a>
    </div>

    <script>
        var dates = {dates_js};
        function makeChart(id, title, name, data, color) {{
            var c = echarts.init(document.getElementById(id));
            c.setOption({{
                tooltip: {{ trigger: 'axis' }},
                xAxis: {{ data: dates }},
                yAxis: {{ scale: true }},
                series: [{{ name: name, type: 'line', data: data, color: color, smooth: true }}]
            }});
        }}
        makeChart('chart_usdcny', 'USD/CNY', '汇率', {usd_cny_vals}, '#e53e3e');
        makeChart('chart_vndcny', 'VND/CNY', '越南盾', {vnd_cny_vals}, '#3182ce');
        
        var cFlight = echarts.init(document.getElementById('chart_flight'));
        cFlight.setOption({{
            tooltip: {{ trigger: 'axis' }},
            legend: {{ data: ['14天后趋势', '2027-02-01'] }},
            xAxis: {{ data: dates }},
            yAxis: {{ scale: true }},
            series: [
                {{ name: '14天后趋势', type: 'line', data: {flight_today_vals}, color: '#f59e0b', smooth: true }},
                {{ name: '2027-02-01', type: 'line', data: {flight_fixed_vals}, color: '#805ad5', smooth: true }}
            ]
        }});
    </script>
</body>
</html>"""
    with open("finance.html", "w", encoding="utf-8") as f: f.write(finance_html)

if __name__ == "__main__":
    main()

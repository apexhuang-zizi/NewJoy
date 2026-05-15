import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import time
from bs4 import BeautifulSoup
import google.generativeai as genai

# ---------- 1. 配置区 ----------
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# ---------- 2. 核心功能：机票抓取 (SerpApi) ----------
def fetch_flight_data_v2(target_date):
    """抓取南航直达机票，人民币计价"""
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        return 0, "<tr><td colspan='3'>未配置 API Key</td></tr>"
    
    # 必须安装了 google-search-results 才能执行下面这行
    from serpapi.google_search import GoogleSearch
    
    params = {
        "engine": "google_flights",
        "departure_id": "SGN",
        "arrival_id": "CAN",
        "outbound_date": target_date,
        "currency": "CNY",  # 人民币计价
        "hl": "zh-cn",
        "api_key": api_key,
        "type": "1",
        "stops": "1"
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        flights = results.get("best_flights", []) + results.get("other_flights", [])
        cz_flights = []
        for f in flights:
            for seg in f.get("flights", []):
                name = seg.get("airline", "")
                if "China Southern" in name or "南方航空" in name:
                    cz_flights.append({
                        "flight_number": seg.get("flight_number", "CZ???"),
                        "price": f.get("price", 0),
                        "departure": seg.get("departure_airport", {}).get("time", "未知")
                    })
        if not cz_flights:
            return 0, "<tr><td colspan='3'>未找到南航直达航班</td></tr>"
        
        cz_flights.sort(key=lambda x: x['price'])
        lowest_price = cz_flights[0]['price']
        rows_html = "".join([f"<tr><td style='padding:8px;border-bottom:1px solid #eee;'>{f['flight_number']}</td><td style='padding:8px;border-bottom:1px solid #eee;'>￥{f['price']}</td><td style='padding:8px;border-bottom:1px solid #eee;'>{f['departure']}</td></tr>" for f in cz_flights[:5]])
        return lowest_price, rows_html
    except Exception as e:
        print(f"机票抓取错误: {e}")
        return 0, "<tr><td colspan='3'>抓取异常</td></tr>"

def fetch_today_flight_price():
    target = (pd.Timestamp.now() + pd.Timedelta(days=14)).strftime('%Y-%m-%d')
    return fetch_flight_data_v2(target)

def fetch_fixed_date_flight():
    return fetch_flight_data_v2("2027-02-01")

# ---------- 3. 股票数据 (越南) ----------
def fetch_stock_prices():
    stocks = ["FPT.VN", "VCB.VN", "VIC.VN", "VNM.VN"]
    data = {}
    for s in stocks:
        try:
            ticker = yf.Ticker(s)
            price = ticker.history(period="1d")['Close'].iloc[-1]
            data[s.split('.')[0]] = round(price, 2)
        except: data[s.split('.')[0]] = 0
    return data

# ---------- 4. 主逻辑 ----------
def main():
    # 模拟抓取汇率（请保留你原代码中那段真正的 BeautifulSoup 抓取逻辑）
    usd_vnd, cny_vnd = 25400, 3500 

    # 机票数据获取
    flight_price, flight_rows_html = fetch_today_flight_price()
    fixed_flight_price, _ = fetch_fixed_date_flight()
    
    stock_data = fetch_stock_prices()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 更新历史 CSV
    history_file = "history.csv"
    if os.path.exists(history_file):
        history_df = pd.read_csv(history_file)
    else:
        history_df = pd.DataFrame(columns=['Date', 'USD_VND', 'CNY_VND', 'Flight_Price', 'Fixed_Flight'])

    new_row = pd.DataFrame([{
        'Date': today_str, 'USD_VND': usd_vnd, 'CNY_VND': cny_vnd, 
        'Flight_Price': flight_price, 'Fixed_Flight': fixed_flight_price
    }])
    history_df = pd.concat([history_df, new_row]).drop_duplicates('Date', keep='last').tail(90)
    history_df.to_csv(history_file, index=False)

    # 股票 CSV
    stock_file = "stock_history.csv"
    if os.path.exists(stock_file):
        stock_df = pd.read_csv(stock_file)
    else:
        stock_df = pd.DataFrame(columns=['Date'] + list(stock_data.keys()))
    
    stock_new_row = pd.DataFrame([{"Date": today_str, **stock_data}])
    stock_df = pd.concat([stock_df, stock_new_row]).drop_duplicates('Date', keep='last').tail(90)
    stock_df.to_csv(stock_file, index=False)

    # 准备图表数据
    dates = history_df['Date'].tolist()
    flight_vals = history_df['Flight_Price'].tolist()
    fixed_vals = history_df['Fixed_Flight'].fillna(0).tolist()
    # 股票系列生成逻辑...
    stock_series = []
    for s_name in stock_data.keys():
        vals = stock_df[s_name].tolist()
        stock_series.append(f"{{ name: '{s_name}', type: 'line', data: {vals}, smooth: true }}")
    stock_series_str = ",".join(stock_series)

    # 生成 HTML
    finance_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>金融看板</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        body {{ font-family: sans-serif; background: #f4f7f6; padding: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ background: #f8f9fa; }}
        .btn {{ padding: 10px 20px; color: white; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }}
    </style>
</head>
<body>
    <div class="card">
        <h3>✈️ 南航直达明细 (SGN → CAN)</h3>
        <table>
            <tr><th>航班号</th><th>价格 (CNY)</th><th>起飞时间</th></tr>
            {flight_rows_html}
        </table>
    </div>

    <div class="card"><div id="chart_flight" style="height:400px;"></div></div>
    <div class="card"><div id="chart_fixed" style="height:400px;"></div></div>
    <div class="card"><div id="chart_stocks" style="height:400px;"></div></div>

    <div style="text-align:center;">
        <a href="history.csv" download class="btn" style="background:#3182ce;">📥 下载汇率机票数据</a>
        <a href="stock_history.csv" download class="btn" style="background:#38a169; margin-left:10px;">📥 下载股票历史数据</a>
    </div>

    <script>
        var dates = {dates};
        var chartF = echarts.init(document.getElementById('chart_flight'));
        chartF.setOption({{
            title: {{ text: '南航票价趋势 (14天后参考)' }},
            tooltip: {{ trigger: 'axis' }},
            xAxis: {{ data: dates }},
            yAxis: {{ name: '人民币 (￥)', scale: true }},
            series: [{{ name: '票价', type: 'line', data: {flight_vals}, color: '#f59e0b', smooth: true }}]
        }});

        var chartFix = echarts.init(document.getElementById('chart_fixed'));
        chartFix.setOption({{
            title: {{ text: '2027-02-01 固定日期追踪' }},
            tooltip: {{ trigger: 'axis' }},
            xAxis: {{ data: dates }},
            yAxis: {{ name: '人民币 (￥)', scale: true }},
            series: [{{ name: '票价', type: 'line', data: {fixed_vals}, color: '#e53e3e', smooth: true }}]
        }});

        var chartS = echarts.init(document.getElementById('chart_stocks'));
        chartS.setOption({{
            title: {{ text: '越南股票趋势' }},
            tooltip: {{ trigger: 'axis' }},
            xAxis: {{ data: dates }},
            yAxis: {{ name: '越南盾', scale: true }},
            series: [{stock_series_str}]
        }});
    </script>
</body>
</html>"""
    with open("finance.html", "w", encoding="utf-8") as f:
        f.write(finance_html)

if __name__ == "__main__":
    main()

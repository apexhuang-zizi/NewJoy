import os
import requests
from datetime import datetime
import random

def fetch_data():
    print("=== 开始数据抓取 ===")
    proxy_url = os.environ.get('MY_PROXY_URL')
    
    if not proxy_url:
        print("❌ 错误：未检测到 PROXY_URL 环境变量")
        return None

    proxies = {"http": proxy_url, "https": proxy_url}
    url = "https://www.kickstarter.com/discover/advanced.json?category_id=16&sort=newest&page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
        print(f"📡 代理响应状态码: {response.status_code}")
        if response.status_code == 200:
            return response.json().get('projects', [])
    except Exception as e:
        print(f"❌ 抓取异常: {e}")
    return None

def write_html(projects):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cards = ""
    if projects:
        for p in projects[:12]:
            name = p.get('name', 'N/A')
            link = p.get('urls', {}).get('web', {}).get('project', '#')
            cards += f'<li><a href="{link}">{name}</a></li>'
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Data Dashboard</title></head>
    <body style="font-family:sans-serif; padding:20px;">
        <h1>Global Trends Monitor</h1>
        <ul>{cards if cards else "<li>No data collected</li>"}</ul>
        <hr>
        <p>Last Update: {now}</p>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ index.html 已生成")

if __name__ == "__main__":
    data = fetch_data()
    write_html(data)

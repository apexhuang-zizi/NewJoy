import os
import requests
from datetime import datetime
import time
import random

def fetch_data():
    print("=== 开始数据抓取 (增强伪装版) ===")
    proxy_url = os.environ.get('MY_PROXY_URL')
    
    if not proxy_url:
        print("❌ 错误：未检测到 PROXY_URL")
        return None

    proxies = {"http": proxy_url, "https": proxy_url}
    
    # 这里的 URL 换一个参数，有时候能绕过缓存拦截
    url = "https://www.kickstarter.com/discover/advanced.json?category_id=16&sort=magic&page=1"
    
    # 核心伪装：加入更完整的请求头，模拟真实浏览器访问
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.kickstarter.com/discover",
        "X-Requested-With": "XMLHttpRequest",
        "DNT": "1"
    }
    
    try:
        # 随机延迟 1-5 秒，模仿人类点击
        wait_time = random.uniform(1, 5)
        print(f"📡 等待 {wait_time:.2f} 秒后发起请求...")
        time.sleep(wait_time)
        
        response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
        print(f"📡 代理响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            return response.json().get('projects', [])
        elif response.status_code == 403:
            print("⚠️ 仍然被拦截 (403)。建议在代理后台更换 IP 节点或国家（如固定为美国）。")
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
            cards += f'<li><a href="{link}" target="_blank">{name}</a></li>'
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Monitor Dashboard</title></head>
    <body style="font-family:sans-serif; padding:20px; line-height:1.6;">
        <h1>Global Trends Monitor</h1>
        <p>Status: {"Success" if projects else "Failed (Check Logs)"}</p>
        <hr>
        <ul>{cards if cards else "<li>No data available - Service Blocked</li>"}</ul>
        <hr>
        <p style="color:#666;">Last Update: {now}</p>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("✅ index.html 已更新")

if __name__ == "__main__":
    data = fetch_data()
    write_html(data)

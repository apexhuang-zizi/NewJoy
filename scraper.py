import requests
import json

def fetch_kickstarter_projects():
    # 2026年实测：直接请求 Kickstarter 的搜索接口比爬网页更稳
    url = "https://www.kickstarter.com/discover/advanced.json?category_id=16&sort=magic&seed=2851417&page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        projects = data.get('projects', [])
        
        results = []
        for p in projects[:10]: # 只取前10个最热门的
            results.append({
                "name": p.get('name'),
                "goal": p.get('goal'),
                "pledged": p.get('pledged'),
                "currency": p.get('currency'),
                "deadline": p.get('deadline'),
                "url": p.get('urls', {}).get('web', {}).get('project'),
                "photo": p.get('photo', {}).get('medium')
            })
        return results
    except Exception as e:
        print(f"数据抓取失败: {e}")
        return []

def generate_html(projects):
    project_cards = ""
    for p in projects:
        percent = int((p['pledged'] / p['goal']) * 100) if p['goal'] > 0 else 0
        project_cards += f"""
        <div class="card">
            <img src="{p['photo']}" style="width:100%; border-radius:8px;">
            <h3><a href="{p['url']}" target="_blank">{p['name']}</a></h3>
            <p>筹款进度: <strong>{percent}%</strong> ({p['pledged']} {p['currency']})</p>
        </div>
        """
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <title>众筹灵感监控站 - 实战版</title>
        <style>
            body {{ font-family: 'PingFang SC', sans-serif; background: #f0f2f5; padding: 20px; }}
            .container {{ max-width: 1000px; margin: auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
            .card {{ background: white; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #1a365d; }}
            a {{ color: #2b6cb0; text-decoration: none; }}
        </style>
    </head>
    <body>
        <h1>🔥 全球硬件众筹热门动态</h1>
        <div class="container">{project_cards}</div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

if __name__ == "__main__":
    data = fetch_kickstarter_projects()
    if data:
        generate_html(data)
        print(f"成功抓取 {len(data)} 个真实项目！")
    else:
        print("未抓取到数据，请检查网络或接口地址。")

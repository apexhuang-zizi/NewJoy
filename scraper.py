import os
import requests
import urllib.parse
from datetime import datetime

def fetch_kickstarter_projects():
    # 1. 从环境变量读取原始信息
    user = os.environ.get('DI_USER')
    password = os.environ.get('DI_PASS')
    host = os.environ.get('DI_HOST')
    
    if not all([user, password, host]):
        print("❌ 错误：GitHub Secrets (DI_USER, DI_PASS, DI_HOST) 配置不全！")
        return None

    # 2. 自动进行 URL 转码，解决空格和特殊字符问题
    encoded_user = urllib.parse.quote_plus(user)
    encoded_pass = urllib.parse.quote_plus(password)
    proxy_url = f"http://{encoded_user}:{encoded_pass}@{host}"
    
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }

    url = "https://www.kickstarter.com/discover/advanced.json?category_id=16&sort=magic&page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    print(f"📡 正在尝试通过代理连接 (目标: {host})...")
    
    try:
        # 增加超时时间到 30 秒
        response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
        response.raise_for_status()
        print("✅ 代理认证成功，数据已获取！")
        return response.json().get('projects', [])
    except requests.exceptions.ProxyError:
        print("❌ 代理连接失败：请检查 DI_HOST 是否正确，或 DataImpulse 服务是否可用。")
    except requests.exceptions.HTTPError as e:
        if "407" in str(e):
            print("❌ 认证失败 (407)：请检查 DataImpulse 的用户名和密码是否正确。")
        else:
            print(f"❌ 网络请求错误: {e}")
    except Exception as e:
        print(f"❌ 发生未知错误: {type(e).__name__} - {e}")
    
    return None

def generate_html(projects):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not projects:
        content = """
        <div style="text-align:center; padding:50px; background:white; border-radius:15px; border: 2px solid #e74c3c;">
            <h2 style="color:#e74c3c;">📡 代理通信故障</h2>
            <p>请点击 GitHub Actions 查看详细报错日志。</p>
            <p>常见原因：1. 密码含特殊字符需重新配置 2. 代理流量耗尽 3. 账号被封禁。</p>
        </div>
        """
    else:
        cards = ""
        for p in projects[:12]:
            goal = p.get('goal', 1)
            pledged = p.get('pledged', 0)
            percent = int((pledged / goal) * 100)
            cards += f"""
            <div style="background:white; padding:15px; border-radius:12px; box-shadow:0 4px 6px rgba(0,0,0,0.05);">
                <img src="{p.get('photo', {}).get('medium')}" style="width:100%; border-radius:8px; height:180px; object-fit:cover;">
                <h3 style="font-size:16px; height:45px; overflow:hidden; margin:10px 0;">{p.get('name')}</h3>
                <div style="background:#eee; height:8px; border-radius:4px;">
                    <div style="background:#27ae60; width:{min(percent, 100)}%; height:100%; border-radius:4px;"></div>
                </div>
                <p style="font-size:14px; color:#666;">进度: <b>{percent}%</b></p>
                <a href="{p.get('urls', {}).get('web', {}).get('project')}" target="_blank" 
                   style="display:block; text-align:center; background:#1a365d; color:white; padding:8px; border-radius:5px; text-decoration:none; margin-top:10px;">
                   查看灵感
                </a>
            </div>
            """
        content = f"""<div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:25px;">{cards}</div>"""

    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head><meta charset="UTF-8"><title>众筹灵感监控站</title></head>
    <body style="font-family:sans-serif; background:#f0f2f5; padding:30px;">
        <h1 style="text-align:center; color:#1a365d;">🚀 全球硬件众筹看板</h1>
        <div style="max-width:1200px; margin:auto;">{content}</div>
        <hr><p style="text-align:center; color:#95a5a6;">最后更新：{now} (UTC) | @ KINGWOOD VIETNAM</p>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

if __name__ == "__main__":
    data = fetch_kickstarter_projects()
    generate_html(data)

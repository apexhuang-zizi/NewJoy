import requests
import os

def fetch_data():
    # 测试阶段：模拟数据
    print("正在抓取数据...")
    return [
        {"title": "智能家居控制中心 2026", "progress": "92%"},
        {"title": "工业级 3D 打印机改装件", "progress": "45%"},
        {"title": "人体工学分体式键盘", "progress": "120%"}
    ]

def generate_html(data):
    # 生成一个更像样的看板页面
    items_html = "".join([f"<li><strong>{i['title']}</strong> - 当前筹款进度: {i['progress']}</li>" for i in data])
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>众筹灵感监控站</title>
        <style>
            body {{ font-family: sans-serif; padding: 40px; line-height: 1.6; color: #333; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            ul {{ list-style: none; padding: 0; }}
            li {{ background: #f4f7f6; margin: 10px 0; padding: 15px; border-radius: 8px; border-left: 5px solid #3498db; }}
        </style>
    </head>
    <body>
        <h1>🚀 国际众筹热门商品（测试版）</h1>
        <ul>{items_html}</ul>
        <p><small>更新时间: {os.popen('date').read()}</small></p>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

if __name__ == "__main__":
    try:
        data = fetch_data()
        generate_html(data)
        print("网页生成成功！")
    except Exception as e:
        print(f"运行出错: {e}")
        exit(1) # 如果出错，通知 GitHub Actions 任务失败

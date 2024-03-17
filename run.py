import os

# from dotenv import load_dotenv
from app import create_app

# 加载环境变量
# load_dotenv()

# 创建 Flask 应用实例
app = create_app(os.getenv("FLASK_CONFIG") or "default")

if __name__ == "__main__":
    # 运行 Flask 应用
    app.run(host="0.0.0.0", port=5000)

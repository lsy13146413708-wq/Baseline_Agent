# =========================
# 基础镜像
# =========================
FROM python:3.10-slim

# =========================
# 工作目录
# =========================
WORKDIR /app

# =========================
# 系统依赖（Graphviz 必须）
# =========================
RUN apt-get update && apt-get install -y \
    graphviz \
    graphviz-dev \
    fonts-noto-cjk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Python 依赖
# =========================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =========================
# 项目代码
# =========================
COPY . .

# =========================
# Streamlit 端口
# =========================
EXPOSE 8501

# =========================
# 启动命令（非常关键）
# =========================
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
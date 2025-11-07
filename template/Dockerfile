# 基于轻量 Python 镜像构建模板自动标注环境
FROM python:3.11-slim

# 安装必要系统依赖（Pillow 图像处理等）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 仅复制并安装标注脚本依赖，利用缓存
COPY template/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 复制脚本到镜像
COPY template/qwen_vl_2dgrounding.py /app/qwen_vl_2dgrounding.py

# 默认工作目录用于挂载宿主的模板目录
WORKDIR /workspace

# 默认入口为脚本，可通过 docker run 追加参数覆盖
ENTRYPOINT ["python", "/app/qwen_vl_2dgrounding.py"]
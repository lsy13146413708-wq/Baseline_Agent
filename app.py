import os
import uuid
import shutil
import subprocess
import sys
from pathlib import Path
import zipfile
import io
import streamlit as st
from streamlit.components.v1 import html as st_html

BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "frontend_outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)


st.set_page_config(page_title="技术路线图生成器", layout="centered")
st.title("技术路线图生成器")
st.write("请放入您需要生成技术路线图的文件")

uploaded = st.file_uploader("拖拽或点击上传文件", type=None)

if uploaded is not None:
  job_id = uuid.uuid4().hex
  filename = uploaded.name
  saved_path = UPLOAD_DIR / f"{job_id}_{filename}"
  with open(saved_path, "wb") as fh:
    fh.write(uploaded.getbuffer())

  out_dir = OUTPUTS_DIR / f"out_{job_id}"
  if out_dir.exists():
    shutil.rmtree(out_dir)
  out_dir.mkdir(parents=True, exist_ok=True)

  with st.spinner('技术路线图正在生成，请耐心等待...'):
    # main.py 期望 --output 是文件前缀（不含扩展名），不是目录路径。
    # 这里构造一个输出前缀：out_dir/roadmap
    output_prefix = out_dir / 'roadmap'
    cmd = [
      sys.executable,
      str(Path(__file__).parent / 'main.py'),
      '--input', str(saved_path),
      '--output', str(output_prefix),
    ]
    try:
      proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60*60)
    except subprocess.TimeoutExpired:
      st.error('处理超时')
      st.stop()

  if proc.returncode != 0:
    st.error('子进程返回错误')
    st.text(proc.stdout)
    st.text(proc.stderr)
  else:
    st.success('生成完成')

    # 查找可预览文件（优先 HTML）
    preview_path = None
    for root, dirs, files in os.walk(out_dir):
      for name in files:
        lower = name.lower()
        if lower.endswith(('.html', '.htm')):
          preview_path = Path(root) / name
          break
      if preview_path:
        break

    if preview_path and preview_path.exists():
      content = preview_path.read_text(encoding='utf-8', errors='ignore')
      st_html(content, height=600, scrolling=True)
    else:
      # 查找文本类型
      text_path = None
      for root, dirs, files in os.walk(out_dir):
        for name in files:
          if name.lower().endswith(('.txt', '.md')):
            text_path = Path(root) / name
            break
        if text_path:
          break

      if text_path and text_path.exists():
        text = text_path.read_text(encoding='utf-8', errors='ignore')
        st.code(text)
      else:
        # 打包为 zip 并提供下载
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
          for root, dirs, files in os.walk(out_dir):
            for name in files:
              file_path = Path(root) / name
              arcname = file_path.relative_to(out_dir)
              zf.write(file_path, arcname)
        buf.seek(0)
        st.download_button('下载生成结果（ZIP）', data=buf, file_name=f'result_{job_id}.zip')

    # 显示子进程输出以便调试
    if proc.stdout:
      st.subheader('子进程输出')
      st.text(proc.stdout)
    if proc.stderr:
      st.subheader('子进程错误输出')
      st.text(proc.stderr)


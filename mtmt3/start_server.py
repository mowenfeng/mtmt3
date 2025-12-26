#!/usr/bin/env python
"""
启动脚本：同时运行FastAPI服务器和后台worker
"""
import subprocess
import sys
import os
from pathlib import Path

# 设置工作目录为项目根目录
project_root = Path(__file__).parent
os.chdir(project_root)

def start_api_server():
    """启动FastAPI服务器"""
    print("=" * 60)
    print("启动FastAPI服务器 (http://127.0.0.1:8000)")
    print("=" * 60)
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--reload", "--port", "8000"],
        cwd=str(project_root)
    )

def start_worker():
    """启动后台worker"""
    print("=" * 60)
    print("启动后台Worker")
    print("=" * 60)
    return subprocess.Popen(
        [sys.executable, "-m", "backend.worker"],
        cwd=str(project_root)
    )

if __name__ == "__main__":
    print("\n🚀 启动音乐转谱服务...\n")
    
    # 启动API服务器
    api_process = start_api_server()
    
    # 等待一下让API服务器启动
    import time
    time.sleep(2)
    
    # 启动worker
    worker_process = start_worker()
    
    print("\n" + "=" * 60)
    print("✅ 服务已启动！")
    print("=" * 60)
    print("📡 API服务器: http://127.0.0.1:8000")
    print("📄 API文档: http://127.0.0.1:8000/docs")
    print("⚙️  Worker: 后台运行中")
    print("\n按 Ctrl+C 停止所有服务\n")
    
    try:
        # 等待进程
        api_process.wait()
        worker_process.wait()
    except KeyboardInterrupt:
        print("\n\n正在停止服务...")
        api_process.terminate()
        worker_process.terminate()
        api_process.wait()
        worker_process.wait()
        print("✅ 服务已停止")

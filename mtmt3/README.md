# 音乐转谱服务

基于MR-MT3模型的音乐转谱服务，支持将音频文件转换为MIDI和MusicXML格式。

## 功能特性

- 🎵 音乐转谱：将音频转录为五线谱与简谱
- 📄 图文识谱：识别五线谱图片/PDF文件（规划中）
- 🎤 人声分离：将音乐分离成人声与伴奏（规划中）
- 🎹 曲谱转换：将MIDI转换为五线谱与简谱（规划中）

## 快速开始

### 1. 安装依赖

```bash
cd mtmt3/backend
pip install -r requirements.txt
```

或者使用提供的批处理文件（Windows）：
```bash
install_dependencies.bat
```

### 2. 启动服务

#### 方式一：同时启动API和Worker（推荐）

**Windows:**
```bash
start_all.bat
```

**Linux/Mac:**
```bash
python start_server.py
```

#### 方式二：分别启动

**启动API服务器：**
```bash
# Windows
start_api.bat

# Linux/Mac (从项目根目录运行)
python -m uvicorn backend.main:app --reload --port 8000
```

**启动Worker（新开一个终端）：**
```bash
# Windows
start_worker.bat

# Linux/Mac
python -m backend.worker
```

#### 方式三：云端轻服务 + 本地GPU远程Worker

适用于云端不带GPU、本地机器有GPU的场景：

1. 云端仅启动 API（不要启动 `backend.worker`）  
2. 本地 GPU 机器运行远程 Worker，主动从云端拉任务并回传结果

```bash
# 本地 GPU 机器
export REMOTE_API_BASE=http://<你的云端地址>
export WORKER_TOKEN=<与云端一致的令牌>
python -m backend.remote_worker
```

云端需设置同一个 `WORKER_TOKEN` 环境变量，用于远程 Worker 鉴权。

### 3. 访问服务

启动服务后，在浏览器中访问：

- **前端用户界面**: http://127.0.0.1:8000
- **API文档**: http://127.0.0.1:8000/docs
- **API地址**: http://127.0.0.1:8000/api

**注意**: 前端页面已集成到API服务中，直接访问 http://127.0.0.1:8000 即可使用完整的用户界面。

## 使用说明

### 通过前端页面使用

1. 打开 `frontend/index.html` 文件
2. 选择音频文件（支持常见音频格式）
3. 选择模型：
   - `mtmt3_piano_vocal`: 钢琴 + 人声
   - `mtmt3_multi`: 多乐器
4. 选择音乐形式：
   - `with_accompaniment`: 带伴奏演唱
   - `a_cappella`: 无伴奏清唱
   - `instrumental`: 纯乐器演奏
5. 选择量化精度（可选）
6. 点击"上传并转谱"
7. 等待处理完成，下载MIDI或MusicXML文件

### 通过API使用

#### 创建转谱任务

```bash
curl -X POST "http://127.0.0.1:8000/api/tasks" \
  -F "file=@your_audio.wav" \
  -F "model=mtmt3_piano_vocal" \
  -F "mode=with_accompaniment" \
  -F "quantization=none"
```

响应：
```json
{
  "task_id": "uuid-string",
  "status": "queued"
}
```

#### 查询任务状态

```bash
curl "http://127.0.0.1:8000/api/tasks/{task_id}"
```

响应：
```json
{
  "task_id": "uuid-string",
  "status": "done",
  "progress": 1.0,
  "result": {
    "midi_url": "/download/{task_id}.mid",
    "musicxml_url": "/download/{task_id}.musicxml",
    "duration": 120.5,
    "note_count": 500
  }
}
```

#### 下载结果文件

```bash
# 下载MIDI
curl "http://127.0.0.1:8000/download/{task_id}.mid" -o output.mid

# 下载MusicXML
curl "http://127.0.0.1:8000/download/{task_id}.musicxml" -o output.musicxml
```

## 项目结构

```
mtmt3/
├── backend/              # 后端服务
│   ├── main.py          # FastAPI应用
│   ├── worker.py        # 后台任务处理
│   ├── config.py        # 配置文件
│   ├── db.py            # 数据库模型
│   ├── requirements.txt # Python依赖
│   └── mtmt3_core/      # 转谱核心模块
│       └── transcriber.py
├── frontend/            # 前端页面
│   └── index.html       # 主页面
├── start_all.bat        # 启动脚本（Windows）
├── start_api.bat        # 启动API（Windows）
├── start_worker.bat     # 启动Worker（Windows）
└── README.md           # 本文件
```

## 技术栈

- **后端**: FastAPI, SQLAlchemy, Uvicorn
- **模型**: MR-MT3 (CPU版本)
- **音频处理**: librosa, torchaudio
- **MIDI处理**: mido, pretty-midi
- **MusicXML**: music21
- **前端**: HTML, CSS, JavaScript

## 注意事项

1. **CPU模式**: 当前使用CPU版本的MR-MT3模型，处理速度较慢，请耐心等待
2. **文件大小**: 建议音频文件不超过20MB，时长不超过10分钟
3. **音频格式**: 支持常见音频格式（wav, mp3, flac等）
4. **数据库**: 使用SQLite存储任务信息，数据库文件位于 `backend/db.sqlite3`
5. **数据目录**: 上传文件和结果文件存储在 `backend/data/` 目录下

## 故障排除

### 服务无法启动

1. 检查Python版本（建议3.8+）
2. 确认所有依赖已正确安装
3. 检查端口8000是否被占用

### 转谱失败

1. 检查音频文件是否损坏
2. 查看worker日志中的错误信息
3. 确认模型文件已正确下载（首次运行会自动下载）

### 前端无法连接API

1. 确认API服务已启动
2. 检查 `frontend/index.html` 中的 `API_BASE` 地址是否正确
3. 检查浏览器控制台是否有CORS错误

## 许可证

本项目仅供学习和研究使用。

## 联系方式

如有问题或建议，请提交Issue或联系开发者。

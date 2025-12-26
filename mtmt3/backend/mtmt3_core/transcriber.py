import os
import time
import threading
from pathlib import Path
import librosa
import numpy as np

# 确保使用CPU
os.environ["CUDA_VISIBLE_DEVICES"] = ""

try:
    from mt3_infer import transcribe
    MT3_AVAILABLE = True
except ImportError:
    MT3_AVAILABLE = False
    print("警告: mt3_infer 未安装，将使用模拟模式")

try:
    from music21 import converter, stream
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False
    print("警告: music21 未安装，无法生成MusicXML文件")


def run_mtmt3(
    audio_path: str,
    model: str,
    mode: str,
    quantization: str,
    output_dir: str,
    progress_callback=None,
):
    """
    使用MR-MT3模型进行音乐转谱（CPU版本）
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    midi_path = out_dir / "result.mid"
    musicxml_path = out_dir / "result.musicxml"

    if not MT3_AVAILABLE:
        # 如果mt3_infer不可用，使用模拟模式
        print("使用模拟模式（mt3_infer未安装）")
        time.sleep(5)
        midi_path.write_bytes(b"dummy midi")
        if MUSIC21_AVAILABLE:
            try:
                # 尝试创建简单的MusicXML
                score = stream.Score()
                score.write('musicxml', musicxml_path)
            except:
                musicxml_path.write_text("<musicxml>dummy</musicxml>", encoding="utf-8")
        else:
            musicxml_path.write_text("<musicxml>dummy</musicxml>", encoding="utf-8")
        
        return {
            "midi_path": str(midi_path),
            "musicxml_path": str(musicxml_path),
            "duration": 120.0,
            "note_count": 500,
        }

    try:
        # 1. 读取音频文件，转换为单声道、16kHz
        if progress_callback:
            progress_callback("loading_audio", 0.10)  # 10%
        print(f"正在加载音频: {audio_path}")
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        print(f"音频加载完成: shape={audio.shape}, sample_rate={sr}")

        # 2. 归一化到 [-1, 1]
        if progress_callback:
            progress_callback("normalizing", 0.15)  # 15%
        max_val = np.max(np.abs(audio))
        if max_val > 1.0:
            audio = audio / max_val
            print(f"已归一化音频，max={max_val:.3f} -> 1.0")

        # 3. 使用MR-MT3进行转谱（CPU版本）
        if progress_callback:
            progress_callback("transcribing", 0.20)  # 20% - 开始转谱
        print("开始使用MR-MT3转谱（CPU版本，可能需要较长时间）...")
        print("提示: CPU处理速度较慢，请耐心等待。处理时间取决于音频长度。")
        
        # 根据model参数选择模型
        model_name = "mr_mt3"  # 默认使用mr_mt3
        if model == "mtmt3_multi":
            model_name = "mr_mt3"  # 多乐器也使用mr_mt3
        
        # 启动进度更新线程（模拟进度，让用户知道系统还在工作）
        progress_stop = threading.Event()
        if progress_callback:
            def update_progress_loop():
                """定期更新进度，从20%慢慢增加到75%"""
                base_progress = 0.20
                max_progress = 0.75
                elapsed = 0
                while not progress_stop.is_set():
                    # 每10秒更新一次进度，减少数据库连接压力
                    time.sleep(10)
                    elapsed += 10
                    # 根据时间线性增加进度（但不超过75%）
                    progress = min(base_progress + (elapsed / 300.0) * (max_progress - base_progress), max_progress)
                    try:
                        progress_callback("transcribing", progress)
                    except Exception as e:
                        # 如果更新失败，静默处理，避免影响主流程
                        pass
            
            progress_thread = threading.Thread(target=update_progress_loop, daemon=True)
            progress_thread.start()
        
        # 转谱过程（这是最耗时的部分，CPU可能需要几分钟）
        try:
            midi = transcribe(
                audio,
                sr=sr,
                model=model_name,
            )
        finally:
            # 停止进度更新线程
            if progress_callback:
                progress_stop.set()
        
        # 转谱完成，更新进度到80%
        if progress_callback:
            progress_callback("transcribing_done", 0.80)  # 80%
        print("转谱完成！")

        # 4. 保存MIDI文件
        if progress_callback:
            progress_callback("saving_midi", 0.85)  # 85%
        print("正在保存MIDI文件...")
        midi.save(str(midi_path))
        print(f"MIDI文件已保存: {midi_path}")

        # 5. 转换为MusicXML
        if progress_callback:
            progress_callback("converting_musicxml", 0.90)  # 90%
        if MUSIC21_AVAILABLE:
            try:
                print("正在转换为MusicXML...")
                score = converter.parse(str(midi_path))
                score.write('musicxml', str(musicxml_path))
                print(f"MusicXML文件已保存: {musicxml_path}")
            except Exception as e:
                print(f"MusicXML转换失败: {e}，将创建占位文件")
                musicxml_path.write_text("<musicxml>conversion_failed</musicxml>", encoding="utf-8")
        else:
            # 如果没有music21，创建占位文件
            musicxml_path.write_text("<musicxml>music21_not_available</musicxml>", encoding="utf-8")

        # 6. 计算音频时长和音符数量
        duration = len(audio) / sr
        
        # 尝试从MIDI中获取音符数量
        note_count = 0
        if MUSIC21_AVAILABLE:
            try:
                score = converter.parse(str(midi_path))
                note_count = len(score.flat.notes)
            except:
                # 如果解析失败，使用估算值
                note_count = int(duration * 4)  # 假设每秒4个音符

        print(f"转谱完成: 时长={duration:.2f}秒, 音符数={note_count}")

        return {
            "midi_path": str(midi_path),
            "musicxml_path": str(musicxml_path),
            "duration": duration,
            "note_count": note_count,
        }

    except Exception as e:
        print(f"转谱过程中出错: {e}")
        import traceback
        traceback.print_exc()
        raise

import time
from pathlib import Path

def run_mtmt3(
    audio_path: str,
    model: str,
    mode: str,
    quantization: str,
    output_dir: str,
):
    """
    真正上线时：
      1. 读取 audio_path
      2. 调用 MR-MT3 推理
      3. 生成 MIDI / MusicXML 文件
    现在先用假数据，确认整体架构没写崩。
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 假装在转谱
    time.sleep(5)

    midi_path = out_dir / "result.mid"
    musicxml_path = out_dir / "result.musicxml"

    midi_path.write_bytes(b"dummy midi")
    musicxml_path.write_text("<musicxml>dummy</musicxml>", encoding="utf-8")

    fake_duration = 120.0
    fake_note_count = 500

    return {
        "midi_path": str(midi_path),
        "musicxml_path": str(musicxml_path),
        "duration": fake_duration,
        "note_count": fake_note_count,
    }

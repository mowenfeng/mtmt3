# file: run_mrmt3.py

from mt3_infer import transcribe
import librosa
import numpy as np

audio_path = "test.wav"
midi_output = "output_mrmt3_new.mid"

# 1. 讀取音訊，單聲道、16k
audio, sr = librosa.load(audio_path, sr=16000, mono=True)
print("音訊載入完成:", audio.shape, "sample rate:", sr)

# 2. 正規化到 [-1, 1]
max_val = np.max(np.abs(audio))
if max_val > 1.0:                   # ← 這裡改回英文 if
    audio = audio / max_val
    print(f"已正規化音訊，max={max_val:.3f} -> 1.0")

# 3. 用 MR-MT3 轉錄
print("開始用 MR-MT3 轉錄（CPU 會很慢，正常）...")
midi = transcribe(
    audio,
    sr=sr,
    model="mr_mt3",                # ← 正確模型名：底線，不是減號
)

# 4. 寫出 MIDI 檔（mido 的 MidiFile 用 save 存檔）
print("轉錄完成，準備寫出 MIDI...")
midi.save(midi_output)

print("已生成:", midi_output)

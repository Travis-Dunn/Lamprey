#!/usr/bin/env python3
"""
make_loop.py — Create a seamless audio loop from a source recording.

Workflow:
  1. Extracts audio from mp4 (or reads wav/ogg directly)
  2. Trims to the selected region
  3. Applies a crossfade splice so the end blends into the start
  4. Normalizes volume
  5. Exports as .ogg (ready for pygame)

Usage:
  python make_loop.py

Requirements:
  pip install numpy scipy
  ffmpeg must be on PATH
"""
import subprocess
import sys
import os
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

# --- SETTINGS (edit these) ------------------------------------------------

INPUT_FILE      = "source.mp4"       # your phone recording (mp4, wav, ogg, etc.)
OUTPUT_FILE     = "elevation.ogg"    # final seamless loop

# Trim region (seconds into the source file).
# Listen to the raw audio first and pick a clean, steady-state section.
# Set both to 0.0 to use the entire file.
TRIM_START      = 1.3
TRIM_END        = 4.0                # 0.0 = end of file

# Crossfade duration for the seamless splice (seconds).
# Longer = smoother loop but eats into usable audio.
# 0.15–0.5s is usually the sweet spot for mechanical sounds.
CROSSFADE_SEC   = 0.3

# Target loop duration AFTER crossfade (seconds).
# The script will warn if your trimmed region is too short.
# Set to 0.0 to keep whatever length results from trimming.
TARGET_DURATION = 0.0

# High-pass filter to remove low-frequency rumble / handling noise
# from phone recordings. Set to 0 to disable.
HIGHPASS_HZ     = 80

# Low-pass filter to remove hiss / high-frequency phone noise.
# Set to 0 to disable.
LOWPASS_HZ      = 6000

# Normalize peak level (0.0–1.0). 0.9 leaves a little headroom.
NORMALIZE_PEAK  = 0.9

# Output quality for ogg encoding (0–10, higher = better quality / bigger file)
OGG_QUALITY     = 6

# --- END SETTINGS ---------------------------------------------------------


def extract_to_wav(input_path, wav_path):
    """Use ffmpeg to extract/convert any audio format to mono WAV."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ac", "1",           # mono
        "-ar", "44100",       # 44.1kHz
        "-sample_fmt", "s16", # 16-bit
        wav_path
    ]
    print(f"  Extracting audio: {input_path} → {wav_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg error:\n{result.stderr}")
        sys.exit(1)


def wav_to_ogg(wav_path, ogg_path, quality):
    """Use ffmpeg to encode WAV to OGG Vorbis."""
    cmd = [
        "ffmpeg", "-y", "-i", wav_path,
        "-c:a", "libvorbis",
        "-q:a", str(quality),
        ogg_path
    ]
    print(f"  Encoding: {wav_path} → {ogg_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg error:\n{result.stderr}")
        sys.exit(1)


def apply_filter(samples, sr, highpass_hz, lowpass_hz):
    """Apply bandpass filtering to clean up phone recordings."""
    filtered = samples.astype(np.float64)

    if highpass_hz > 0:
        sos = butter(4, highpass_hz, btype='high', fs=sr, output='sos')
        filtered = sosfilt(sos, filtered)
        print(f"  Applied high-pass filter: {highpass_hz} Hz")

    if lowpass_hz > 0:
        sos = butter(4, lowpass_hz, btype='low', fs=sr, output='sos')
        filtered = sosfilt(sos, filtered)
        print(f"  Applied low-pass filter: {lowpass_hz} Hz")

    return filtered


def crossfade_loop(samples, crossfade_n):
    """
    Create a seamless loop by crossfading the tail into the head.

    Takes the last `crossfade_n` samples and blends them with the first
    `crossfade_n` samples, then trims so the result loops perfectly.
    """
    n = len(samples)
    if crossfade_n * 2 >= n:
        print(f"  WARNING: crossfade ({crossfade_n} samples) is too long "
              f"for audio ({n} samples). Reducing to 1/3 of audio length.")
        crossfade_n = n // 3

    # The loop body is everything except the last crossfade_n samples
    body = samples[:-crossfade_n].copy()

    # The tail that wraps around
    tail = samples[-crossfade_n:]
    head = samples[:crossfade_n]

    # Linear crossfade (tail fades out, head fades in)
    fade_out = np.linspace(1.0, 0.0, crossfade_n)
    fade_in  = np.linspace(0.0, 1.0, crossfade_n)

    blended = tail * fade_out + head * fade_in

    # Replace the start of body with the blended region
    body[:crossfade_n] = blended

    print(f"  Crossfade: {crossfade_n} samples "
          f"({crossfade_n / 44100:.3f}s)")
    return body


def main():
    print("=" * 60)
    print("  make_loop.py — Seamless Audio Loop Creator")
    print("=" * 60)

    if not os.path.isfile(INPUT_FILE):
        print(f"\n  ERROR: Input file '{INPUT_FILE}' not found.")
        print(f"  Place your recording in this directory and update INPUT_FILE.")
        sys.exit(1)

    # Step 1: Extract to WAV
    temp_wav = "_temp_extracted.wav"
    extract_to_wav(INPUT_FILE, temp_wav)

    # Step 2: Read WAV
    sr, raw = wavfile.read(temp_wav)
    print(f"  Loaded: {sr} Hz, {len(raw)} samples, "
          f"{len(raw)/sr:.2f}s")

    # Convert to float64 for processing
    if raw.dtype == np.int16:
        samples = raw.astype(np.float64) / 32768.0
    elif raw.dtype == np.float32 or raw.dtype == np.float64:
        samples = raw.astype(np.float64)
    else:
        samples = raw.astype(np.float64) / np.iinfo(raw.dtype).max

    # If stereo somehow, take first channel
    if samples.ndim > 1:
        samples = samples[:, 0]

    # Step 3: Trim
    start_sample = int(TRIM_START * sr)
    end_sample   = int(TRIM_END * sr) if TRIM_END > 0 else len(samples)
    end_sample   = min(end_sample, len(samples))
    samples = samples[start_sample:end_sample]
    print(f"  Trimmed: {TRIM_START:.2f}s – {end_sample/sr:.2f}s "
          f"→ {len(samples)/sr:.2f}s")

    if len(samples) / sr < 0.2:
        print("  ERROR: Trimmed audio is too short (< 0.2s). "
              "Adjust TRIM_START / TRIM_END.")
        sys.exit(1)

    # Step 4: Filter
    samples = apply_filter(samples, sr, HIGHPASS_HZ, LOWPASS_HZ)

    # Step 5: Crossfade loop
    crossfade_n = int(CROSSFADE_SEC * sr)
    samples = crossfade_loop(samples, crossfade_n)
    print(f"  Loop duration: {len(samples)/sr:.3f}s")

    # Step 6: Normalize
    peak = np.max(np.abs(samples))
    if peak > 0:
        samples = samples * (NORMALIZE_PEAK / peak)
        print(f"  Normalized: peak was {peak:.4f}, "
              f"now {NORMALIZE_PEAK:.2f}")

    # Step 7: Write intermediate WAV
    loop_wav = "_temp_loop.wav"
    out_16 = np.clip(samples * 32768.0, -32768, 32767).astype(np.int16)
    wavfile.write(loop_wav, sr, out_16)

    # Step 8: Encode to OGG
    wav_to_ogg(loop_wav, OUTPUT_FILE, OGG_QUALITY)

    # Cleanup temp files
    for f in [temp_wav, loop_wav]:
        if os.path.isfile(f):
            os.remove(f)

    duration = len(samples) / sr
    file_size = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"\n  ✓ Done! → {OUTPUT_FILE}")
    print(f"    Duration:  {duration:.3f}s")
    print(f"    File size: {file_size:.1f} KB")
    print(f"\n  To test the loop, play it on repeat:")
    print(f"    ffplay -loop 0 {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
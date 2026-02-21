import subprocess
from pydub import AudioSegment

# --- SETTINGS (edit these) ---
INPUT_FILE  = "src.mkv"   # put your MKV filename here
OUTPUT_FILE = "loop_sound.ogg"  # what you want the result saved as
LOOP_START  = 1700              # where your loop begins, in milliseconds
LOOP_END    = 2200              # where your loop ends, in milliseconds
CROSSFADE   = 400               # smoothing at the loop point (ms), 50-200 is good
# -----------------------------y

# Step 1: Pull the audio out of the MKV
subprocess.run(["ffmpeg", "-i", INPUT_FILE, "-vn", "-acodec", "pcm_s16le",
                "-ar", "44100", "-ac", "2", "temp_audio.wav"])

# Step 2: Trim and smooth the loop
audio = AudioSegment.from_wav("temp_audio.wav")
loop  = audio[LOOP_START:LOOP_END]
loop  = loop.append(loop, crossfade=CROSSFADE)[:len(loop)]

# Step 3: Save it
loop.export(OUTPUT_FILE, format="ogg")
print("All done! Saved as", OUTPUT_FILE)
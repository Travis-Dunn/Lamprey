from pydub import AudioSegment

audio = AudioSegment.from_wav("extracted_audio.wav")

# Trim to your loop region (times in milliseconds)
loop_start = 1000   # 1 second in
loop_end   = 8000   # 8 seconds in
loop = audio[loop_start:loop_end]

# Crossfade the end back into the beginning to smooth the seam
# The crossfade duration should be short — 50-200ms is usually good
crossfade_ms = 100
looped = loop.append(loop, crossfade=crossfade_ms)

# You now have a double-length clip with a smooth loop point in the middle.
# Trim it back to single length:
looped = looped[:len(loop)]
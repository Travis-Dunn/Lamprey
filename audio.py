"""
Tank Gunner - Audio Manager
Dedicated channel slots with volume ramping for layered sound.

Usage:
    audio = AudioManager()
    audio.register("traverse", "sounds/traverse.ogg", loop=True)
    audio.register("fire",     "sounds/fire.ogg",     loop=False)

    # Each frame:
    audio.set_active("traverse", True)   # ramps volume up
    audio.set_active("traverse", False)  # ramps volume down
    audio.play_oneshot("fire")           # plays immediately
    audio.update(dt)
"""
import os
import pygame
from settings import AUDIO_RAMP_TIME, AUDIO_MASTER_VOLUME


class _ChannelSlot:
    """One named audio slot with its own mixer channel."""

    def __init__(self, channel, sound, loop, base_volume):
        self.channel = channel
        self.sound = sound
        self.loop = loop
        self.base_volume = base_volume

        # Ramping state
        self.target_volume = 0.0
        self.current_volume = 0.0
        self.active = False
        self._started = False  # whether the channel is currently playing

    def set_active(self, active):
        """Request this slot to ramp on or off (for looping sounds)."""
        self.active = active
        self.target_volume = self.base_volume if active else 0.0

    def play_oneshot(self, volume=None):
        """Fire-and-forget play at full volume (for non-looping sounds)."""
        vol = volume if volume is not None else self.base_volume
        self.channel.set_volume(vol * AUDIO_MASTER_VOLUME)
        self.channel.play(self.sound)

    def update(self, dt):
        """Ramp volume toward target; start/stop the channel as needed."""
        if not self.loop:
            return

        # Ramp toward target
        if AUDIO_RAMP_TIME > 0:
            ramp_speed = self.base_volume / AUDIO_RAMP_TIME
        else:
            ramp_speed = float('inf')

        if self.current_volume < self.target_volume:
            self.current_volume = min(
                self.current_volume + ramp_speed * dt,
                self.target_volume)
        elif self.current_volume > self.target_volume:
            self.current_volume = max(
                self.current_volume - ramp_speed * dt,
                self.target_volume)

        # Start looping if we need sound and it's not playing
        if self.current_volume > 0 and not self._started:
            self.channel.play(self.sound, loops=-1)
            self._started = True

        # Apply volume
        if self._started:
            self.channel.set_volume(self.current_volume * AUDIO_MASTER_VOLUME)

        # Stop once fully faded out
        if self.current_volume <= 0 and self._started:
            self.channel.stop()
            self._started = False


class AudioManager:
    """Manages named audio channel slots."""

    def __init__(self):
        pygame.mixer.set_num_channels(8)
        self._slots = {}       # name → _ChannelSlot
        self._next_chan = 0     # channel index counter

    def register(self, name, filepath, loop=False, base_volume=1.0):
        """
        Register a named sound.  Call once during setup.
        Returns False (with a warning) if the file is missing so the
        game can still run without audio assets.
        """
        if not os.path.isfile(filepath):
            print(f"[audio] WARNING: '{filepath}' not found — "
                  f"'{name}' will be silent")
            return False

        sound = pygame.mixer.Sound(filepath)
        channel = pygame.mixer.Channel(self._next_chan)
        self._next_chan += 1

        self._slots[name] = _ChannelSlot(
            channel, sound, loop, base_volume)
        return True

    def set_active(self, name, active):
        """Ramp a looping sound on or off."""
        slot = self._slots.get(name)
        if slot:
            slot.set_active(active)

    def play_oneshot(self, name, volume=None):
        """Play a one-shot sound immediately."""
        slot = self._slots.get(name)
        if slot:
            slot.play_oneshot(volume)

    def update(self, dt):
        """Call once per frame to process volume ramps."""
        for slot in self._slots.values():
            slot.update(dt)
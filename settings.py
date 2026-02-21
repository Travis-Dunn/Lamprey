"""
Tank Gunner - Settings & Constants
All tunable game parameters in one place.
"""
import math

# ── Display ──────────────────────────────────────────────
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
WINDOW_TITLE = "Tank Gunner"

# ── Gunsight ─────────────────────────────────────────────
SIGHT_RADIUS = 250                          # pixels
SIGHT_FOV_DEG = 12.0                        # field of view in degrees
SIGHT_FOV_RAD = math.radians(SIGHT_FOV_DEG)
# Focal length for projection (pixels per unit at z=1)
SIGHT_FOCAL = SIGHT_RADIUS / math.tan(SIGHT_FOV_RAD / 2.0)

# ── Colors ───────────────────────────────────────────────
COL_BLACK       = (0, 0, 0)
COL_SKY         = (155, 195, 230)
COL_GROUND      = (95, 130, 60)
COL_GROUND_LINE = (82, 115, 52)
COL_RETICLE     = (20, 20, 20)
COL_TANK_BODY   = (55, 58, 48)
COL_READY       = (30, 220, 30)
COL_RELOADING   = (220, 60, 20)
COL_WHITE       = (255, 255, 255)
COL_HUD_TEXT    = (200, 200, 200)
COL_DUST        = (190, 170, 110)
COL_HIT         = (255, 90, 20)

# ── Gun Controls ─────────────────────────────────────────
TRAVERSE_SPEED_DEG      = 1.5               # degrees per second (fine/slow)
TRAVERSE_SPEED_FAST_DEG = 24.0              # degrees per second (shift held)
TRAVERSE_RAMP_TIME      = 0.5              # seconds to reach full fast speed
ELEVATION_SPEED_DEG = 4.0
RELOAD_TIME         = 5.0                   # seconds
MIN_ELEVATION_DEG   = -4.0
MAX_ELEVATION_DEG   = 20.0
INITIAL_ELEVATION_DEG = 1.5
INITIAL_TRAVERSE_DEG  = 0.0

# ── Player ───────────────────────────────────────────────
PLAYER_EYE_HEIGHT = 2.2                     # meters (turret hatch height)

# ── Ballistics ───────────────────────────────────────────
SHELL_MUZZLE_VELOCITY = 750.0              # m/s
GRAVITY               = 9.81               # m/s²
SHELL_MASS            = 10.2               # kg  (~88mm AP)
# Simplified drag: deceleration = DRAG_K * v²
# Tuned so shell loses ~120 m/s over 1000m
DRAG_K                = 0.00018
DISPERSION_STD_RAD    = 0.00035            # ~0.35m @ 1000m
SIM_DT                = 0.002              # simulation timestep (s)
SHELL_MAX_TIME        = 10.0               # max flight time (s)

# ── Enemy Tank (meters) ─────────────────────────────────
TANK_LENGTH = 6.5                           # along Z (front-to-back)
TANK_WIDTH  = 3.2                           # along X
TANK_HEIGHT = 2.4                           # along Y

# ── Engagement ───────────────────────────────────────────
SPAWN_RANGE_MIN = 500.0                     # meters
SPAWN_RANGE_MAX = 1500.0
SPAWN_LATERAL_MAX = 200.0                   # meters off-center

# ── Tracer ───────────────────────────────────────────────
TRACER_TRAIL_LENGTH  = 8                    # number of past positions to draw
TRACER_SAMPLE_INTERVAL = 0.015              # seconds between trail samples
TRACER_COLOR         = (255, 230, 140)      # warm bright yellow
TRACER_CORE_COLOR    = (255, 255, 220)      # bright white-yellow core
TRACER_MAX_RADIUS    = 4                    # pixels at close range
TRACER_MIN_RADIUS    = 1                    # pixels at far range

# ── Spotter Callouts ────────────────────────────────────
SPOTTER_DISPLAY_TIME   = 4.0               # seconds to show callout
SPOTTER_FADE_TIME      = 1.0               # seconds of fade at end
SPOTTER_ROUND_TO       = 50                # round distance corrections to this (meters)
SPOTTER_MIN_CORRECTION = 10                # below this, call it "on target"

# ── Effects ──────────────────────────────────────────────
EXPLOSION_DURATION   = 1.8                  # seconds
DUST_BASE_RADIUS     = 18                   # pixels in sight (scaled by distance)
HIT_BASE_RADIUS      = 25

# ── Audio ────────────────────────────────────────────────
AUDIO_MASTER_VOLUME = 0.8                   # 0.0–1.0 global volume
AUDIO_RAMP_TIME     = 0.15                  # seconds for looping sounds to fade in/out
AUDIO_TRAVERSE_VOL  = 0.6                   # base volume for traverse motor
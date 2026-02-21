"""
Tank Gunner - World Simulation
3D positions, ballistic shell simulation, and collision detection.
All coordinates: X = right, Y = up, Z = forward.
"""
import math
import random
import numpy as np
from settings import *


# ── Vector helpers ───────────────────────────────────────

def vec3(x, y, z):
    return np.array([x, y, z], dtype=np.float64)


def normalize(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


# ── Projection helpers ──────────────────────────────────

def get_view_basis(elevation_rad, traverse_rad):
    """
    Return (forward, right, up) vectors for the gun direction.
    Traverse = yaw from +Z.  Elevation = pitch up from horizontal.
    """
    ce = math.cos(elevation_rad)
    se = math.sin(elevation_rad)
    ct = math.cos(traverse_rad)
    st = math.sin(traverse_rad)

    forward = vec3(st * ce, se, ct * ce)
    # Right = forward × world_up  (left-hand cross would flip, but we want
    # screen-X to increase rightward, which matches this convention)
    world_up = vec3(0.0, 1.0, 0.0)
    right = normalize(np.cross(forward, world_up))
    up = np.cross(right, forward)          # already unit length
    return forward, right, up


def project_to_sight(point_3d, eye_pos, forward, right, up):
    """
    Project a 3D world point into sight-space pixel offsets (sx, sy)
    relative to the sight center.  Returns None if the point is behind
    the camera or outside a generous clip region.
    sy is positive downward (screen convention).
    """
    delta = point_3d - eye_pos
    z = float(np.dot(delta, forward))
    if z < 0.5:                            # behind or too close
        return None
    x = float(np.dot(delta, right))
    y = float(np.dot(delta, up))
    sx = x / z * SIGHT_FOCAL
    sy = -y / z * SIGHT_FOCAL              # flip for screen Y
    return (sx, sy)


# ── Player Gun ──────────────────────────────────────────

class PlayerGun:
    def __init__(self):
        self.eye = vec3(0.0, PLAYER_EYE_HEIGHT, 0.0)
        self.elevation = math.radians(INITIAL_ELEVATION_DEG)
        self.traverse = math.radians(INITIAL_TRAVERSE_DEG)
        self.reload_timer = 0.0            # 0 = ready
        self.ready = True
        self._traverse_ramp = 0.0          # ramp-up timer for fast traverse

    def update(self, dt, keys_held):
        """Process input and update gun state."""
        import pygame

        # Determine traverse speed with ramp-up for fast mode
        shift_held = keys_held[pygame.K_LSHIFT] or keys_held[pygame.K_RSHIFT]
        traversing = keys_held[pygame.K_a] or keys_held[pygame.K_d]

        if shift_held and traversing:
            # Ramp up toward fast speed
            self._traverse_ramp = min(self._traverse_ramp + dt,
                                      TRAVERSE_RAMP_TIME)
        else:
            # Reset ramp when shift released or not traversing
            self._traverse_ramp = 0.0

        # Lerp between slow and fast based on ramp progress
        t = self._traverse_ramp / TRAVERSE_RAMP_TIME if TRAVERSE_RAMP_TIME > 0 else 1.0
        traverse_speed = math.radians(
            TRAVERSE_SPEED_DEG + (TRAVERSE_SPEED_FAST_DEG - TRAVERSE_SPEED_DEG) * t
        )

        # Traverse (A/D keys)
        if keys_held[pygame.K_a]:
            self.traverse += traverse_speed * dt
        if keys_held[pygame.K_d]:
            self.traverse -= traverse_speed * dt

        # Elevation (arrow keys up/down)
        if keys_held[pygame.K_UP]:
            self.elevation += math.radians(ELEVATION_SPEED_DEG) * dt
        if keys_held[pygame.K_DOWN]:
            self.elevation -= math.radians(ELEVATION_SPEED_DEG) * dt

        # Clamp elevation
        self.elevation = max(math.radians(MIN_ELEVATION_DEG),
                             min(math.radians(MAX_ELEVATION_DEG), self.elevation))

        # Reload timer
        if not self.ready:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.reload_timer = 0.0
                self.ready = True

    def fire(self):
        """Attempt to fire. Returns a Shell or None."""
        if not self.ready:
            return None
        self.ready = False
        self.reload_timer = RELOAD_TIME

        # Gun direction with dispersion
        elev = self.elevation + random.gauss(0, DISPERSION_STD_RAD)
        trav = self.traverse + random.gauss(0, DISPERSION_STD_RAD)

        forward, _, _ = get_view_basis(elev, trav)
        velocity = forward * SHELL_MUZZLE_VELOCITY
        # Shell starts slightly ahead of eye to avoid self-intersection
        start_pos = self.eye + forward * 2.0
        return Shell(start_pos, velocity)

    def get_view(self):
        """Return (forward, right, up) for the current aim direction."""
        return get_view_basis(self.elevation, self.traverse)


# ── Shell ────────────────────────────────────────────────

class Shell:
    def __init__(self, position, velocity):
        self.pos = position.copy()
        self.vel = velocity.copy()
        self.alive = True
        self.time = 0.0
        # Tracer trail
        self.trail = [position.copy()]
        self._trail_timer = 0.0

    def step(self, dt):
        """Advance one simulation step. Returns (prev_pos, curr_pos)."""
        prev = self.pos.copy()

        # Drag: deceleration proportional to v²
        speed = np.linalg.norm(self.vel)
        if speed > 0:
            drag_decel = DRAG_K * speed * speed
            self.vel -= normalize(self.vel) * drag_decel * dt

        # Gravity
        self.vel[1] -= GRAVITY * dt

        # Integrate position
        self.pos = self.pos + self.vel * dt
        self.time += dt

        # Record trail samples at regular intervals
        self._trail_timer += dt
        if self._trail_timer >= TRACER_SAMPLE_INTERVAL:
            self._trail_timer = 0.0
            self.trail.append(self.pos.copy())
            if len(self.trail) > TRACER_TRAIL_LENGTH:
                self.trail.pop(0)

        if self.time > SHELL_MAX_TIME:
            self.alive = False

        return prev, self.pos.copy()


# ── Enemy Tank ──────────────────────────────────────────

class EnemyTank:
    """Axis-aligned bounding box sitting on the ground plane."""
    def __init__(self, x, z, heading_deg=0.0):
        self.center = vec3(x, TANK_HEIGHT / 2.0, z)
        self.alive = True
        self.destroyed = False
        # Half-extents
        self.hx = TANK_WIDTH / 2.0
        self.hy = TANK_HEIGHT / 2.0
        self.hz = TANK_LENGTH / 2.0

    @property
    def aabb_min(self):
        return self.center - vec3(self.hx, self.hy, self.hz)

    @property
    def aabb_max(self):
        return self.center + vec3(self.hx, self.hy, self.hz)

    def get_box_corners(self):
        """Return the 8 corners of the bounding box."""
        mn = self.aabb_min
        mx = self.aabb_max
        return [
            vec3(mn[0], mn[1], mn[2]),
            vec3(mx[0], mn[1], mn[2]),
            vec3(mx[0], mx[1], mn[2]),
            vec3(mn[0], mx[1], mn[2]),
            vec3(mn[0], mn[1], mx[2]),
            vec3(mx[0], mn[1], mx[2]),
            vec3(mx[0], mx[1], mx[2]),
            vec3(mn[0], mx[1], mx[2]),
        ]

    def get_silhouette_quads(self):
        """
        Return a list of 4-corner face quads suitable for projection.
        We return all 6 faces; the renderer will cull back-faces.
        """
        mn = self.aabb_min
        mx = self.aabb_max
        # Each face as 4 corners in CCW order when viewed from outside
        return [
            # Front  (−Z face)
            [vec3(mn[0], mn[1], mn[2]), vec3(mx[0], mn[1], mn[2]),
             vec3(mx[0], mx[1], mn[2]), vec3(mn[0], mx[1], mn[2])],
            # Back   (+Z face)
            [vec3(mx[0], mn[1], mx[2]), vec3(mn[0], mn[1], mx[2]),
             vec3(mn[0], mx[1], mx[2]), vec3(mx[0], mx[1], mx[2])],
            # Left   (−X face)
            [vec3(mn[0], mn[1], mx[2]), vec3(mn[0], mn[1], mn[2]),
             vec3(mn[0], mx[1], mn[2]), vec3(mn[0], mx[1], mx[2])],
            # Right  (+X face)
            [vec3(mx[0], mn[1], mn[2]), vec3(mx[0], mn[1], mx[2]),
             vec3(mx[0], mx[1], mx[2]), vec3(mx[0], mx[1], mn[2])],
            # Top    (+Y face)
            [vec3(mn[0], mx[1], mn[2]), vec3(mx[0], mx[1], mn[2]),
             vec3(mx[0], mx[1], mx[2]), vec3(mn[0], mx[1], mx[2])],
            # Bottom (−Y face)
            [vec3(mn[0], mn[1], mx[2]), vec3(mx[0], mn[1], mx[2]),
             vec3(mx[0], mn[1], mn[2]), vec3(mn[0], mn[1], mn[2])],
        ]


# ── Collision ────────────────────────────────────────────

def segment_aabb_intersect(p0, p1, aabb_min, aabb_max):
    """
    Test whether the line segment p0→p1 intersects the AABB.
    Returns the intersection point (numpy vec3) or None.
    Uses the slab method.
    """
    d = p1 - p0
    tmin = 0.0
    tmax = 1.0

    for i in range(3):
        if abs(d[i]) < 1e-12:
            # Ray parallel to slab
            if p0[i] < aabb_min[i] or p0[i] > aabb_max[i]:
                return None
        else:
            inv_d = 1.0 / d[i]
            t1 = (aabb_min[i] - p0[i]) * inv_d
            t2 = (aabb_max[i] - p0[i]) * inv_d
            if t1 > t2:
                t1, t2 = t2, t1
            tmin = max(tmin, t1)
            tmax = min(tmax, t2)
            if tmin > tmax:
                return None

    return p0 + d * tmin


def check_ground_hit(prev_pos, curr_pos):
    """
    Check if the shell crossed the ground plane (Y=0) between steps.
    Returns the ground-plane intersection point or None.
    """
    if curr_pos[1] <= 0.0 and prev_pos[1] > 0.0:
        # Lerp to find intersection
        t = prev_pos[1] / (prev_pos[1] - curr_pos[1])
        hit = prev_pos + (curr_pos - prev_pos) * t
        hit[1] = 0.0
        return hit
    return None


# ── World Manager ────────────────────────────────────────

class World:
    def __init__(self):
        self.gun = PlayerGun()
        self.tanks = []
        self.shells = []           # active shells in flight
        self.explosions = []       # list of (pos_3d, is_hit, timer)
        self.spotter_callouts = [] # list of {'text':str, 'timer':float, ...}
        self.score = 0
        self.shots_fired = 0
        self.spawn_tank()

    def spawn_tank(self):
        """Spawn a new enemy tank at a random position."""
        z = random.uniform(SPAWN_RANGE_MIN, SPAWN_RANGE_MAX)
        x = random.uniform(-SPAWN_LATERAL_MAX, SPAWN_LATERAL_MAX)
        self.tanks.append(EnemyTank(x, z))

    def _nearest_live_tank(self):
        """Return the nearest alive tank, or None."""
        best = None
        best_dist = float('inf')
        for t in self.tanks:
            if t.alive:
                d = float(np.linalg.norm(t.center - self.gun.eye))
                if d < best_dist:
                    best_dist = d
                    best = t
        return best

    def _generate_spotter_callout(self, impact_pos, is_hit):
        """Generate a spotter correction callout based on impact position."""
        if is_hit:
            self.spotter_callouts.append({
                'lines': ["TARGET HIT!"],
                'timer': SPOTTER_DISPLAY_TIME,
                'max_time': SPOTTER_DISPLAY_TIME,
                'is_hit': True,
            })
            return

        target = self._nearest_live_tank()
        if target is None:
            return

        # Compute correction relative to target
        # Range correction: positive = long (impact beyond target)
        # Lateral correction: positive = right
        target_center = target.center.copy()
        target_center[1] = 0.0  # compare on ground plane
        impact_ground = impact_pos.copy()
        impact_ground[1] = 0.0

        # Direction from player to target
        to_target = target_center - self.gun.eye
        to_target[1] = 0.0
        target_range = float(np.linalg.norm(to_target))
        if target_range < 1.0:
            return

        forward_dir = to_target / target_range
        # Right direction (perpendicular on ground plane)
        right_dir = vec3(forward_dir[2], 0.0, -forward_dir[0])

        # Vector from target to impact
        delta = impact_ground - target_center
        range_err = float(np.dot(delta, forward_dir))   # + = long
        lateral_err = float(np.dot(delta, right_dir))   # + = right

        lines = []

        # Range callout
        abs_range = abs(range_err)
        if abs_range < SPOTTER_MIN_CORRECTION:
            lines.append("RANGE: ON")
        else:
            rounded = max(SPOTTER_ROUND_TO,
                          int(round(abs_range / SPOTTER_ROUND_TO) * SPOTTER_ROUND_TO))
            if range_err > 0:
                lines.append(f"LONG {rounded}m — DROP")
            else:
                lines.append(f"SHORT {rounded}m — ADD")

        # Lateral callout
        abs_lat = abs(lateral_err)
        if abs_lat < SPOTTER_MIN_CORRECTION:
            lines.append("LINE: ON")
        else:
            rounded = max(SPOTTER_ROUND_TO,
                          int(round(abs_lat / SPOTTER_ROUND_TO) * SPOTTER_ROUND_TO))
            if lateral_err > 0:
                lines.append(f"RIGHT {rounded}m")
            else:
                lines.append(f"LEFT {rounded}m")

        self.spotter_callouts.append({
            'lines': lines,
            'timer': SPOTTER_DISPLAY_TIME,
            'max_time': SPOTTER_DISPLAY_TIME,
            'is_hit': False,
        })

    def fire(self):
        """Player fires the gun. Returns True if shell was fired."""
        shell = self.gun.fire()
        if shell:
            self.shells.append(shell)
            self.shots_fired += 1
            return True
        return False

    def update(self, dt, keys_held):
        """Advance the entire world by dt seconds."""
        self.gun.update(dt, keys_held)

        # Simulate each shell
        finished_shells = []
        for shell in self.shells:
            if not shell.alive:
                finished_shells.append(shell)
                continue

            # Run multiple sim steps per frame for accuracy
            remaining = dt
            hit = False
            while remaining > 0 and shell.alive:
                step_dt = min(SIM_DT, remaining)
                prev, curr = shell.step(step_dt)
                remaining -= step_dt

                # Check tank hits
                for tank in self.tanks:
                    if not tank.alive:
                        continue
                    hit_pt = segment_aabb_intersect(
                        prev, curr, tank.aabb_min, tank.aabb_max)
                    if hit_pt is not None:
                        # Hit!
                        tank.alive = False
                        tank.destroyed = True
                        self.score += 1
                        self.explosions.append({
                            'pos': hit_pt.copy(),
                            'is_hit': True,
                            'timer': EXPLOSION_DURATION,
                            'max_time': EXPLOSION_DURATION,
                        })
                        self._generate_spotter_callout(hit_pt, is_hit=True)
                        shell.alive = False
                        hit = True
                        break

                if hit:
                    break

                # Check ground hit
                ground_pt = check_ground_hit(prev, curr)
                if ground_pt is not None:
                    self.explosions.append({
                        'pos': ground_pt.copy(),
                        'is_hit': False,
                        'timer': EXPLOSION_DURATION,
                        'max_time': EXPLOSION_DURATION,
                    })
                    self._generate_spotter_callout(ground_pt, is_hit=False)
                    shell.alive = False
                    break

            if not shell.alive:
                finished_shells.append(shell)

        for s in finished_shells:
            if s in self.shells:
                self.shells.remove(s)

        # Update explosions
        for exp in self.explosions:
            exp['timer'] -= dt
        self.explosions = [e for e in self.explosions if e['timer'] > 0]

        # Update spotter callouts
        for callout in self.spotter_callouts:
            callout['timer'] -= dt
        self.spotter_callouts = [c for c in self.spotter_callouts
                                  if c['timer'] > 0]

        # Respawn destroyed tanks after a short delay
        if all(not t.alive for t in self.tanks):
            # Clear dead tanks and spawn a new one
            self.tanks = []
            self.spawn_tank()
"""
Tank Gunner - Renderer
All drawing goes through here: sight picture, ground plane,
tank silhouettes, reticle, HUD indicators, and explosion effects.
"""
import math
import pygame
from settings import *
from world import project_to_sight, vec3


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.cx = SCREEN_WIDTH // 2
        self.cy = SCREEN_HEIGHT // 2

        # Pre-create a circular clipping surface for the sight
        self.sight_surface = pygame.Surface(
            (SIGHT_RADIUS * 2, SIGHT_RADIUS * 2), pygame.SRCALPHA)
        # Mask: transparent outside the circle
        self.sight_mask = pygame.Surface(
            (SIGHT_RADIUS * 2, SIGHT_RADIUS * 2), pygame.SRCALPHA)
        pygame.draw.circle(
            self.sight_mask, (255, 255, 255, 255),
            (SIGHT_RADIUS, SIGHT_RADIUS), SIGHT_RADIUS)

        self.font_small = pygame.font.SysFont("consolas", 18)
        self.font_large = pygame.font.SysFont("consolas", 26, bold=True)
        self.font_gauge = pygame.font.SysFont("consolas", 12)

    # ── Coordinate helpers ───────────────────────────────

    def _sight_to_screen(self, sx, sy):
        """Convert sight-relative coords to screen coords."""
        return (int(self.cx + sx), int(self.cy + sy))

    def _in_sight(self, sx, sy, margin=0):
        """Check if sight-relative point is inside the sight circle."""
        return sx * sx + sy * sy <= (SIGHT_RADIUS + margin) ** 2

    # ── Main draw call ───────────────────────────────────

    def draw(self, world):
        """Draw everything for one frame."""
        self.screen.fill(COL_BLACK)

        gun = world.gun
        forward, right, up = gun.get_view()
        eye = gun.eye

        # Draw into the sight surface
        self.sight_surface.fill((0, 0, 0, 0))
        self._draw_sky_and_ground(gun, forward, right, up, eye)
        self._draw_ground_lines(forward, right, up, eye)
        self._draw_tanks(world.tanks, forward, right, up, eye)
        self._draw_explosions(world.explosions, forward, right, up, eye)
        self._draw_tracers(world.shells, forward, right, up, eye)
        self._draw_reticle()

        # Apply circular mask
        masked = self.sight_surface.copy()
        masked.blit(self.sight_mask, (0, 0),
                     special_flags=pygame.BLEND_RGBA_MIN)

        # Blit sight onto main screen
        self.screen.blit(
            masked,
            (self.cx - SIGHT_RADIUS, self.cy - SIGHT_RADIUS))

        # Draw sight border ring
        pygame.draw.circle(
            self.screen, (40, 40, 40),
            (self.cx, self.cy), SIGHT_RADIUS + 3, 6)
        pygame.draw.circle(
            self.screen, (80, 80, 80),
            (self.cx, self.cy), SIGHT_RADIUS + 1, 2)

        # HUD elements (outside the sight)
        self._draw_hud(world)
        self._draw_azimuth_gauge(world)
        self._draw_elevation_gauge(world)
        self._draw_spotter_callouts(world)

    # ── Sky & ground fill ────────────────────────────────

    def _draw_sky_and_ground(self, gun, forward, right, up, eye):
        """Fill the sight with sky above horizon, ground below."""
        r = SIGHT_RADIUS
        surf = self.sight_surface

        # Horizon line Y in sight coords:
        # The horizon is at elevation angle 0. Our view is at gun.elevation.
        # The horizon appears at  sy = SIGHT_FOCAL * tan(elevation)
        horizon_sy = SIGHT_FOCAL * math.tan(gun.elevation)

        # Fill entire sight with sky
        pygame.draw.circle(surf, COL_SKY, (r, r), r)

        # Fill below horizon with ground
        # Convert horizon_sy to surface coords
        horizon_surf_y = r + horizon_sy  # surface Y

        if horizon_surf_y < r * 2:
            # There is ground visible
            ground_rect = pygame.Rect(0, int(horizon_surf_y), r * 2,
                                       int(r * 2 - horizon_surf_y) + 1)
            pygame.draw.rect(surf, COL_GROUND, ground_rect)

    # ── Ground perspective lines ─────────────────────────

    def _draw_ground_lines(self, forward, right, up, eye):
        """Draw horizontal lines at regular depth intervals for depth cues."""
        r = SIGHT_RADIUS
        surf = self.sight_surface

        # Project lines at distances 100, 200, ... 2000m
        for dist in range(100, 2001, 100):
            # Two points on the ground at this distance, spread wide
            points_2d = []
            for x_off in [-500, 500]:
                pt = vec3(x_off, 0.0, float(dist))
                proj = project_to_sight(pt, eye, forward, right, up)
                if proj:
                    sx, sy = proj
                    if abs(sx) < r * 2 and abs(sy) < r * 2:
                        points_2d.append((r + sx, r + sy))

            if len(points_2d) == 2:
                # Fade lines with distance
                alpha = max(30, 160 - dist // 8)
                col = (
                    COL_GROUND_LINE[0],
                    COL_GROUND_LINE[1],
                    COL_GROUND_LINE[2],
                    alpha
                )
                pygame.draw.line(surf, col, points_2d[0], points_2d[1], 1)

    # ── Tank rendering ───────────────────────────────────

    def _draw_tanks(self, tanks, forward, right, up, eye):
        """Project and draw enemy tanks as filled silhouettes."""
        r = SIGHT_RADIUS
        surf = self.sight_surface

        for tank in tanks:
            if not tank.alive:
                continue

            # Project all faces
            faces = tank.get_silhouette_quads()
            for face_corners in faces:
                # Back-face culling: compute face normal direction toward eye
                # Simple: check if the face center is facing us
                fc = sum(c for c in face_corners) / 4.0
                face_to_eye = eye - fc
                # Compute face normal via cross product of two edges
                e1 = face_corners[1] - face_corners[0]
                e2 = face_corners[3] - face_corners[0]
                import numpy as np
                normal = np.cross(e1, e2)
                if np.dot(normal, face_to_eye) <= 0:
                    continue  # back face

                # Project corners
                projected = []
                for corner in face_corners:
                    p = project_to_sight(corner, eye, forward, right, up)
                    if p is None:
                        break
                    projected.append((r + p[0], r + p[1]))

                if len(projected) == 4:
                    # Shade faces differently for depth
                    # Darken side/top faces slightly
                    if abs(normal[1]) > 0.5:
                        col = (75, 78, 65)     # top
                    elif abs(normal[0]) > 0.5:
                        col = (50, 52, 44)     # sides
                    else:
                        col = COL_TANK_BODY     # front/back
                    pygame.draw.polygon(surf, col, projected)
                    pygame.draw.polygon(surf, (35, 35, 30), projected, 1)

    # ── Explosions ───────────────────────────────────────

    def _draw_explosions(self, explosions, forward, right, up, eye):
        """Draw explosion effects at their 3D positions."""
        r = SIGHT_RADIUS
        surf = self.sight_surface

        for exp in explosions:
            proj = project_to_sight(exp['pos'], eye, forward, right, up)
            if proj is None:
                continue
            sx, sy = proj
            if not self._in_sight(sx, sy, margin=50):
                continue

            # Explosion progress (1.0 → 0.0)
            progress = exp['timer'] / exp['max_time']
            # Expand then fade
            expand = 1.0 - (progress - 0.5) ** 2 * 4  # peaks at 0.5
            expand = max(0.3, min(1.0, expand * 1.5))

            # Distance-based size scaling
            dist = float(exp['pos'][2])  # rough distance
            dist = max(dist, 50.0)
            size_scale = 600.0 / dist

            if exp['is_hit']:
                base_col = COL_HIT
                base_r = HIT_BASE_RADIUS
            else:
                base_col = COL_DUST
                base_r = DUST_BASE_RADIUS

            px_r = max(3, int(base_r * expand * size_scale))
            alpha = int(255 * progress)
            alpha = max(0, min(255, alpha))

            # Draw glow layers
            for layer in range(3, 0, -1):
                lr = px_r * layer // 2
                la = alpha // layer
                glow_col = (
                    min(255, base_col[0] + 40 * (3 - layer)),
                    min(255, base_col[1] + 20 * (3 - layer)),
                    base_col[2],
                    la
                )
                center = (int(r + sx), int(r + sy))
                pygame.draw.circle(surf, glow_col, center, lr)

    # ── Tracers ───────────────────────────────────────────

    def _draw_tracers(self, shells, forward, right, up, eye):
        """Draw bright tracer trails for in-flight shells."""
        r = SIGHT_RADIUS
        surf = self.sight_surface

        for shell in shells:
            if not shell.alive:
                continue

            trail = shell.trail
            n = len(trail)
            if n < 1:
                continue

            # Also include current position as the head
            all_points = trail + [shell.pos.copy()]

            # Project each trail point and draw with fading intensity
            total = len(all_points)
            prev_screen = None
            for i, point in enumerate(all_points):
                proj = project_to_sight(point, eye, forward, right, up)
                if proj is None:
                    prev_screen = None
                    continue

                sx, sy = proj
                screen_pt = (int(r + sx), int(r + sy))

                # Age factor: 0.0 (oldest) to 1.0 (newest/head)
                age = i / max(1, total - 1)

                # Distance-based size
                dist = float(point[2])
                dist = max(50.0, dist)
                dist_scale = 400.0 / dist

                # Radius: larger at head, smaller for tail
                px_r = max(TRACER_MIN_RADIUS,
                           int(TRACER_MAX_RADIUS * age * dist_scale))

                # Alpha: fade the tail
                alpha = int(255 * age)
                alpha = max(30, min(255, alpha))

                # Draw connecting line segment for the streak
                if prev_screen is not None and age > 0.1:
                    streak_alpha = int(180 * age)
                    streak_col = (
                        TRACER_COLOR[0], TRACER_COLOR[1], TRACER_COLOR[2],
                        max(20, streak_alpha)
                    )
                    pygame.draw.line(surf, streak_col, prev_screen, screen_pt,
                                     max(1, px_r))

                # Draw the point itself
                if self._in_sight(sx, sy, margin=10):
                    # Outer glow
                    glow_r = px_r + 2
                    glow_col = (
                        TRACER_COLOR[0], TRACER_COLOR[1], TRACER_COLOR[2],
                        max(10, alpha // 3)
                    )
                    pygame.draw.circle(surf, glow_col, screen_pt, glow_r)

                    # Core
                    core_col = (
                        TRACER_CORE_COLOR[0], TRACER_CORE_COLOR[1],
                        TRACER_CORE_COLOR[2], alpha
                    )
                    pygame.draw.circle(surf, core_col, screen_pt, px_r)

                prev_screen = screen_pt

    # ── Reticle ──────────────────────────────────────────

    def _draw_reticle(self):
        """Draw crosshair reticle on the sight."""
        r = SIGHT_RADIUS
        surf = self.sight_surface
        col = (*COL_RETICLE, 180)

        gap = 12           # gap at center
        length = 60        # line length from gap
        thickness = 1

        # Horizontal lines
        pygame.draw.line(surf, col,
                         (r - gap - length, r), (r - gap, r), thickness)
        pygame.draw.line(surf, col,
                         (r + gap, r), (r + gap + length, r), thickness)
        # Vertical lines
        pygame.draw.line(surf, col,
                         (r, r - gap - length), (r, r - gap), thickness)
        pygame.draw.line(surf, col,
                         (r, r + gap), (r, r + gap + length), thickness)

        # Center dot
        pygame.draw.circle(surf, col, (r, r), 2)

        # Mil-dot style range marks below center
        for i in range(1, 5):
            y_off = i * 25
            tick_w = 6
            pygame.draw.line(surf, col,
                             (r - tick_w, r + gap + y_off),
                             (r + tick_w, r + gap + y_off), thickness)

    # ── HUD ──────────────────────────────────────────────

    def _draw_hud(self, world):
        """Draw reload indicator, score, and range estimate."""
        gun = world.gun

        # ── Reload indicator ─────────────────────────────
        ind_x = self.cx + SIGHT_RADIUS + 40
        ind_y = self.cy - 30
        ind_w, ind_h = 20, 60

        if gun.ready:
            pygame.draw.rect(
                self.screen, COL_READY,
                (ind_x, ind_y, ind_w, ind_h))
            label = self.font_small.render("READY", True, COL_READY)
        else:
            # Fill proportional to reload progress
            prog = 1.0 - (gun.reload_timer / RELOAD_TIME)
            fill_h = int(ind_h * prog)
            pygame.draw.rect(
                self.screen, (60, 60, 60),
                (ind_x, ind_y, ind_w, ind_h))
            pygame.draw.rect(
                self.screen, COL_RELOADING,
                (ind_x, ind_y + ind_h - fill_h, ind_w, fill_h))
            label = self.font_small.render("LOAD", True, COL_RELOADING)

        pygame.draw.rect(
            self.screen, (100, 100, 100),
            (ind_x, ind_y, ind_w, ind_h), 1)
        self.screen.blit(label, (ind_x - 4, ind_y + ind_h + 6))

        # ── Score ────────────────────────────────────────
        score_txt = self.font_large.render(
            f"KILLS: {world.score}", True, COL_HUD_TEXT)
        self.screen.blit(score_txt, (20, 20))

        if world.shots_fired > 0:
            acc = world.score / world.shots_fired * 100
            acc_txt = self.font_small.render(
                f"ACC: {acc:.0f}%  ({world.score}/{world.shots_fired})",
                True, COL_HUD_TEXT)
            self.screen.blit(acc_txt, (20, 52))

        # ── Range to nearest tank ────────────────────────
        for tank in world.tanks:
            if tank.alive:
                dx = tank.center[0] - gun.eye[0]
                dz = tank.center[2] - gun.eye[2]
                dist = math.sqrt(dx * dx + dz * dz)
                # Don't show exact range (player should estimate)
                # but show a rough indicator
                range_txt = self.font_small.render(
                    f"TGT: ~{int(dist / 100) * 100}m", True, COL_HUD_TEXT)
                self.screen.blit(range_txt,
                                 (SCREEN_WIDTH - range_txt.get_width() - 20, 20))
                break

    # ── Azimuth Gauge (M19) ──────────────────────────────

    def _draw_azimuth_gauge(self, world):
        """
        Draw a simplified M19 Azimuth Indicator below the sight.

        Fixed outer ring with tick marks numbered 0 (hull forward)
        to 50 (hull rear), identical on both sides.  Rotating inner
        pointer shows current turret facing.
        """
        gun = world.gun
        r = AZIMUTH_GAUGE_RADIUS

        # Center position: below the sight
        gx = self.cx
        gy = self.cy + SIGHT_RADIUS + 20 + r

        # ── Background & bezel ───────────────────────────
        pygame.draw.circle(self.screen, GAUGE_BG_COLOR, (gx, gy), r)
        pygame.draw.circle(self.screen, GAUGE_RING_COLOR, (gx, gy), r, 2)
        # Inner ring where the pointer lives
        pygame.draw.circle(self.screen, GAUGE_RING_COLOR,
                           (gx, gy), r - 18, 1)

        # ── Outer ring tick marks (0–50 each side) ───────
        # Each M19 unit = pi/50 radians of turret rotation.
        # Drawing convention:  angle = 0 at 12 o'clock, positive = CW.
        #   screen x = gx + r * sin(angle)
        #   screen y = gy - r * cos(angle)
        for side in (1, -1):                # +1 = right (CW), -1 = left (CCW)
            for unit in range(0, AZIMUTH_M19_MAX + 1):
                if side == -1 and (unit == 0 or unit == AZIMUTH_M19_MAX):
                    continue                # 0 and 50 shared between sides

                angle = side * unit * math.pi / AZIMUTH_M19_MAX
                sa = math.sin(angle)
                ca = math.cos(angle)

                # Tick length depends on significance
                if unit % 10 == 0:
                    tick_inner = r - 16
                    tick_outer = r - 3
                    draw_number = True
                elif unit % 5 == 0:
                    tick_inner = r - 12
                    tick_outer = r - 3
                    draw_number = True
                else:
                    tick_inner = r - 8
                    tick_outer = r - 3
                    draw_number = False

                x1 = gx + sa * tick_outer
                y1 = gy - ca * tick_outer
                x2 = gx + sa * tick_inner
                y2 = gy - ca * tick_inner
                pygame.draw.line(self.screen, GAUGE_MARK_COLOR,
                                 (int(x1), int(y1)),
                                 (int(x2), int(y2)), 1)

                # Number labels
                if draw_number:
                    label = self.font_gauge.render(str(unit), True,
                                                   GAUGE_MARK_COLOR)
                    lw, lh = label.get_size()
                    nr = r - 24              # number radius
                    nx = gx + sa * nr - lw / 2
                    ny = gy - ca * nr - lh / 2
                    self.screen.blit(label, (int(nx), int(ny)))

        # ── Hull-forward lubber line ─────────────────────
        pygame.draw.line(self.screen, GAUGE_LUBBER_COLOR,
                         (gx, gy - r + 2),
                         (gx, gy - r + 14), 3)

        # ── Turret pointer (rotates with traverse) ───────
        # Positive traverse = turret left → pointer goes CCW on dial
        # so screen angle = -traverse  (CW positive in our drawing)
        ptr_angle = -gun.traverse
        ptr_len = r - 20
        px = gx + math.sin(ptr_angle) * ptr_len
        py = gy - math.cos(ptr_angle) * ptr_len

        # Draw pointer line
        pygame.draw.line(self.screen, GAUGE_NEEDLE_COLOR,
                         (gx, gy), (int(px), int(py)), 2)
        # Tail nub (short line opposite the pointer)
        tail_len = 10
        tx = gx - math.sin(ptr_angle) * tail_len
        ty = gy + math.cos(ptr_angle) * tail_len
        pygame.draw.line(self.screen, GAUGE_NEEDLE_COLOR,
                         (gx, gy), (int(tx), int(ty)), 2)
        # Center pivot dot
        pygame.draw.circle(self.screen, GAUGE_NEEDLE_COLOR, (gx, gy), 3)

    # ── Elevation Gauge ──────────────────────────────────

    def _draw_elevation_gauge(self, world):
        """
        Draw a qualitative arc gauge for gun elevation,
        left of the sight.  No tick marks — just an arc with
        end-stops and a needle.  Gives the player the kind of
        coarse feel a real gunner had from the breech position
        and resistance in the elevation wheel.
        """
        gun = world.gun
        arc_r = ELEV_ARC_RADIUS

        # Pivot position: left of sight, vertically centered
        gx = self.cx - SIGHT_RADIUS - 50
        gy = self.cy + 10

        # Map elevation to a visual needle angle.
        # Convention:  needle direction measured as an angle from
        # the negative-X axis (pointing left), positive = upward.
        #   screen_x = gx - arc_r * cos(dir)
        #   screen_y = gy - arc_r * sin(dir)
        min_elev = math.radians(MIN_ELEVATION_DEG)
        max_elev = math.radians(MAX_ELEVATION_DEG)
        t = (gun.elevation - min_elev) / (max_elev - min_elev)
        t = max(0.0, min(1.0, t))

        vis_min = math.radians(ELEV_VISUAL_MIN_DEG)
        vis_max = math.radians(ELEV_VISUAL_MAX_DEG)
        needle_dir = vis_min + t * (vis_max - vis_min)

        # ── Arc track ────────────────────────────────────
        arc_pts = []
        steps = 48
        for i in range(steps + 1):
            d = vis_min + (vis_max - vis_min) * i / steps
            x = gx - arc_r * math.cos(d)
            y = gy - arc_r * math.sin(d)
            arc_pts.append((int(x), int(y)))
        if len(arc_pts) > 1:
            pygame.draw.lines(self.screen, GAUGE_RING_COLOR,
                              False, arc_pts, 2)

        # ── End-stops (pegs) ─────────────────────────────
        for d in (vis_min, vis_max):
            sx = int(gx - arc_r * math.cos(d))
            sy = int(gy - arc_r * math.sin(d))
            pygame.draw.circle(self.screen, GAUGE_MARK_COLOR,
                               (sx, sy), ELEV_STOP_RADIUS)

        # ── Needle ───────────────────────────────────────
        nx = gx - arc_r * 0.9 * math.cos(needle_dir)
        ny = gy - arc_r * 0.9 * math.sin(needle_dir)
        pygame.draw.line(self.screen, GAUGE_NEEDLE_COLOR,
                         (gx, gy), (int(nx), int(ny)), 2)
        # Pivot dot
        pygame.draw.circle(self.screen, GAUGE_NEEDLE_COLOR, (gx, gy), 3)

    # ── Spotter Callouts ─────────────────────────────────

    def _draw_spotter_callouts(self, world):
        """Draw spotter correction callouts to the left of the sight."""
        if not world.spotter_callouts:
            return

        # Show the most recent callout
        callout = world.spotter_callouts[-1]
        progress = callout['timer'] / callout['max_time']

        # Fade out in the last second
        if callout['timer'] < SPOTTER_FADE_TIME:
            alpha = int(255 * callout['timer'] / SPOTTER_FADE_TIME)
        else:
            alpha = 255

        # Position: left of the sight
        base_x = self.cx - SIGHT_RADIUS - 220
        base_y = self.cy - 40

        # Background panel
        panel_w = 200
        line_h = 28
        panel_h = len(callout['lines']) * line_h + 20
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, int(alpha * 0.6)))
        self.screen.blit(panel_surf, (base_x, base_y))

        # "SPOTTER:" header
        header = self.font_small.render("SPOTTER:", True,
                                         (180, 180, 160))
        if alpha < 255:
            header.set_alpha(alpha)
        self.screen.blit(header, (base_x + 10, base_y + 4))

        # Callout lines
        for i, line in enumerate(callout['lines']):
            if callout['is_hit']:
                col = COL_READY
                font = self.font_large
            else:
                col = (255, 220, 100)
                font = self.font_large

            txt = font.render(line, True, col)
            if alpha < 255:
                txt.set_alpha(alpha)
            self.screen.blit(txt,
                             (base_x + 10, base_y + 22 + i * line_h))
# Tank Gunner — Project Seed Prompt

Use this prompt to bring a new Claude instance up to speed on this project. Paste it at the start of a conversation, optionally followed by relevant source files.

---

## The Developer

Freelance SWE whose day job is meteorological/drone tooling software. Pivoting to game development — that's what originally drew them to programming. Has a significantly larger game project in progress. This small project exists specifically as a low-stakes practice run for the full release pipeline: Steam page management, handling feedback, patching, dealing with reviews. The developer is experienced, writes clean code, and thinks carefully about design. Don't over-explain fundamentals.

## The Project

**Tank Gunner** is a very small commercial game targeting a ~$4 price point on Steam. Revenue expectations are modest (a few hundred dollars would be fine). Good reviews matter more than sales — this is a portfolio piece and pipeline rehearsal.

Development timeline is meant to be short. Time is the scarcest resource. Every design and engineering decision should be evaluated against "does this justify the time it costs?" The game is a side project for a side project.

## Game Identity

The game is half simulator, half arcade game, styled to be reminiscent of a 2005-era Flash game. Low-fidelity 2D rendering — a black screen with a circular gunsight in the center and HUD widgets around it. The lo-fi aesthetic serves two purposes: it's fast to produce, and it deliberately undercuts realism expectations so the player doesn't judge the simulation against full-fidelity tank sims.

Despite the simple visuals, the underlying simulation is physically grounded: real ballistics with drag and dispersion, real-scale distances, no aim assists, no target highlighting, no HUD markers. The player sees what a gunner would see through period-appropriate optics. This contrast — serious simulation behind toy graphics — is core to the game's identity.

## Player Experience

The player is an American tank gunner (Sherman, 75mm) starting in 1943. The game simulates not just combat but the arc of a deployment through WWII. Structure:

- **~12 missions** across **3-4 deployments** in different theaters/campaigns (North Africa, Sicily, Italy, France — not yet finalized).
- Missions are played **in fixed order, once only**, no replays within a playthrough (though the player can start a new game).
- Missions **cannot be traditionally failed or succeeded**. The player always moves forward.
- **Death is possible** in many missions but is not "game over" — it ends the playthrough early and shows a coffin with a draped flag.
- **Surviving all missions** leads to a V-E Day ending screen.
- The variable-length playthrough (you might die in mission 4 or survive all 12) gives weight to both endings.
- **Performance is acknowledged but failure is not punished.** The game never tells the player they did poorly. Good performance is rewarded with medal citations, newspaper excerpts, and similar. The player decides what "winning" means to them.
- Between missions, the player reads narrative text: briefings, aftermath, letters, period flavor.

## Player Action Space

Extremely constrained, by design:

- **Traverse** the gun (A/D keys, with shift for fast traverse and ramp-up)
- **Elevate** the gun (W/S keys)
- **Fire** (spacebar, with reload time)

That's it. The game gets its depth from the difficulty of acquiring and hitting targets at real scale through a narrow optic, not from a wide action space. Any expansion to this should be evaluated skeptically — it must make the game better without costing much.

## World Simulation Architecture

**Do NOT build a general-purpose entity/AI system.** The game is 12 missions played once each. The architecture is:

### Shared primitives (engine-level):
- **Target**: position, hitbox dimensions, alive/dead, visible/hidden, optional movement along a path, optional appear/disappear schedule. Represents anything the player might shoot — a tank, a gun emplacement, a muzzle flash position, a vehicle.
- **Visual events**: transient effects at 3D positions — muzzle flashes, dust puffs, explosions. Timer-driven, no logic.
- **Mission state**: arbitrary per-mission counters and timers (infantry casualties, ammo remaining, time elapsed, enemies destroyed, etc.). The mission script reads and writes these; the HUD can display relevant ones.
- **Shell simulation and collision detection**: already implemented, physically grounded with drag, gravity, dispersion, segment-AABB intersection.

### Per-mission scripts (content-level):
Each mission is its own class/module with an `update(dt)` method that orchestrates behavior using the shared primitives. All interesting scenario logic lives here. Examples:

- **Sniper mission**: Target appears at semi-random positions along a treeline on a timer. A casualty counter ticks up from mortar fire. Mission ends when sniper is killed or casualties hit threshold.
- **Convoy ambush**: Targets move along a polyline path at set speed. Player engages as many as possible before they exit.
- **Defensive position**: Tanks spawn at increasing intervals and advance toward the player. Mission ends on a timer or when a tank closes to a threshold distance.
- **Training range**: Static targets at known distances. Tutorial/warm-up.

This keeps engine code thin and lets each mission feel completely different. A mission script is typically 100-200 lines of straightforward Python. No pathfinding, no tactical AI, no cover systems, no detection/visibility systems. If the sniper needs to "choose" between positions, that's a weighted random pick in the script, not an agent decision.

## Example Mission — "The Sniper" (representative, not final)

**Briefing:** Infantry platoon advancing through farmland has been pinned by a sniper in a distant treeline (~600m). A mortar is also engaging the infantry. Your tank can't cross a muddy field to close the distance. Neutralize the sniper from current position.

**Gameplay:** The sniper is a tiny, briefly-visible target (muzzle flash / movement) at long range in a treeline. He moves between positions. The player must spot him, estimate range, and fire. The mortar creates time pressure via an infantry casualty counter. Ammo is limited enough that blind fire is costly but possible if the player has identified the pattern.

**Tuning levers:** Sniper visibility (contrast/size of flash), distance, mortar casualty rate, number of sniper positions, ammo count.

**Medal condition:** Kill the sniper quickly with minimal infantry casualties.

**Sim requirements:** A target that appears/disappears on a schedule at positions along a treeline. A casualty counter on a timer. Visual effects for muzzle flash and mortar impacts. Shell-to-hitbox collision. That's it.

## Technical Stack

- **Python + Pygame + NumPy**
- Rendering: all done through a circular sight surface with projection math (3D world positions → sight-space pixel offsets). No sprites, no tile maps. Everything is drawn procedurally.
- Audio: channel-based system with volume ramping for looping sounds (traverse motor, elevation motor) and one-shot sounds (gun fire).
- The codebase is currently split into: `main.py` (game loop), `settings.py` (all constants), `world.py` (simulation, ballistics, collision), `renderer.py` (all drawing), `audio.py` (sound management).

## Design Principles (in priority order)

1. **Minimize development time.** This is a practice-run side project. Every feature must justify its time cost.
2. **Earn good reviews.** Emotional resonance > mechanical depth. The narrative framing, the once-through structure, the death-as-ending — these are what people will remember and write about.
3. **Keep scope locked.** 12 missions, two endings, minimal player actions. Resist feature creep.
4. **Fake it, don't simulate it.** If a mission-specific script can sell the experience, don't build a general system. Bespoke beats generic here.
5. **Physical grounding where the player touches it.** Ballistics, optics, range estimation — these should feel real because they ARE the gameplay. Everything the player doesn't directly interact with can be as fake as needed.

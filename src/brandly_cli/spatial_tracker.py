"""Spatial tracker — maintains camera and actor positions across shots.

Provides 3D spatial understanding for multi-shot sequences, ensuring
physical continuity and preventing spatial confusion in AI-generated video.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Position3D:
    """A 3D position in scene space."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def distance_to(self, other: Position3D) -> float:
        """Calculate Euclidean distance to another position."""
        return (
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        ) ** 0.5

    def lerp(self, other: Position3D, t: float) -> Position3D:
        """Linear interpolation between two positions."""
        return Position3D(
            x=self.x + (other.x - self.x) * t,
            y=self.y + (other.y - self.y) * t,
            z=self.z + (other.z - self.z) * t,
        )

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {"x": self.x, "y": self.y, "z": self.z}

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> Position3D:
        """Create from dictionary."""
        return cls(x=d.get("x", 0.0), y=d.get("y", 0.0), z=d.get("z", 0.0))


@dataclass
class CameraState:
    """Complete camera state for a shot."""

    position: Position3D = field(default_factory=Position3D)
    look_at: Position3D = field(default_factory=Position3D)
    focal_length_mm: float = 50.0
    sensor_width_mm: float = 36.0
    roll_degrees: float = 0.0
    movement: str = "static"
    movement_speed: float = 1.0

    @property
    def field_of_view(self) -> float:
        """Calculate horizontal field of view in degrees."""
        import math
        return 2 * math.degrees(
            math.atan(self.sensor_width_mm / (2 * self.focal_length_mm))
        )

    @property
    def depth_of_field_description(self) -> str:
        """Describe approximate DOF characteristics."""
        if self.focal_length_mm < 35:
            return "wide depth of field, most in focus"
        elif self.focal_length_mm < 85:
            return "moderate depth of field, subject sharp"
        else:
            return "shallow depth of field, creamy bokeh"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "position": self.position.to_dict(),
            "look_at": self.look_at.to_dict(),
            "focal_length_mm": self.focal_length_mm,
            "sensor_width_mm": self.sensor_width_mm,
            "roll_degrees": self.roll_degrees,
            "movement": self.movement,
            "movement_speed": self.movement_speed,
        }


@dataclass
class ActorState:
    """Complete actor/subject state for a shot."""

    name: str
    position: Position3D = field(default_factory=Position3D)
    facing_direction: str = "forward"
    action: str = "standing"
    eyeline: str = "camera"
    height_units: float = 1.75

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "position": self.position.to_dict(),
            "facing_direction": self.facing_direction,
            "action": self.action,
            "eyeline": self.eyeline,
            "height_units": self.height_units,
        }


class SpatialTracker:
    """Tracks camera and actor positions across shots.

    Maintains spatial continuity by:
    - Tracking camera position and orientation per shot
    - Tracking actor positions and movements
    - Detecting spatial inconsistencies
    - Generating spatial continuity prompts
    """

    def __init__(self, scene_scale: float = 1.0) -> None:
        self.scene_scale = scene_scale
        self._shots: list[dict[str, Any]] = []
        self._cameras: list[CameraState] = []
        self._actors: dict[str, list[ActorState]] = {}
        self._180_rule_violations: list[str] = []

    def add_shot(
        self,
        shot_index: int,
        camera: CameraState,
        actors: list[ActorState] | None = None,
        environment_bounds: tuple[float, float, float] | None = None,
    ) -> None:
        """Record the spatial state for a shot.

        Args:
            shot_index: Sequential shot number.
            camera: Camera state for this shot.
            actors: List of actor states in this shot.
            environment_bounds: (width, height, depth) of the scene space.
        """
        shot_data = {
            "index": shot_index,
            "camera": camera,
            "actors": actors or [],
            "environment_bounds": environment_bounds,
        }
        self._shots.append(shot_data)
        self._cameras.append(camera)

        # Track actor positions
        for actor in (actors or []):
            if actor.name not in self._actors:
                self._actors[actor.name] = []
            self._actors[actor.name].append(actor)

        # Check 180-degree rule
        if len(self._cameras) > 1:
            self._check_180_rule(shot_index)

    def _check_180_rule(self, shot_index: int) -> None:
        """Check if the 180-degree rule is violated between shots."""
        if len(self._cameras) < 2:
            return

        prev = self._cameras[-2]
        curr = self._cameras[-1]

        # Calculate the axis between previous camera and its subject
        if self._shots[-2]["actors"]:
            subject_pos = self._shots[-2]["actors"][0].position
            axis_x = subject_pos.x - prev.position.x
            axis_z = subject_pos.z - prev.position.z

            # Check if current camera crosses the axis
            cross_product = (
                axis_x * (curr.position.z - prev.position.z)
                - axis_z * (curr.position.x - prev.position.x)
            )

            if cross_product < 0:
                self._180_rule_violations.append(
                    f"Shot {shot_index}: 180-degree rule violation — "
                    f"camera crossed the action axis"
                )

    def get_actor_position(self, actor_name: str, shot_index: int) -> Position3D | None:
        """Get an actor's position at a specific shot."""
        if actor_name in self._actors:
            positions = self._actors[actor_name]
            if shot_index < len(positions):
                return positions[shot_index].position
        return None

    def get_camera_movement_vector(self, from_shot: int, to_shot: int) -> Position3D | None:
        """Calculate the camera movement vector between two shots."""
        if from_shot < len(self._cameras) and to_shot < len(self._cameras):
            from_pos = self._cameras[from_shot].position
            to_pos = self._cameras[to_shot].position
            return Position3D(
                x=to_pos.x - from_pos.x,
                y=to_pos.y - from_pos.y,
                z=to_pos.z - from_pos.z,
            )
        return None

    def validate_spatial_continuity(self) -> list[str]:
        """Validate spatial continuity across all shots.

        Returns a list of spatial issues found.
        """
        issues: list[str] = []

        # Check 180-degree rule violations
        issues.extend(self._180_rule_violations)

        # Check for teleporting actors
        for actor_name, positions in self._actors.items():
            for i in range(1, len(positions)):
                prev_pos = positions[i - 1].position
                curr_pos = positions[i].position
                distance = prev_pos.distance_to(curr_pos)

                # If actor moved more than scene_scale in one cut, flag it
                if distance > self.scene_scale * 2:
                    issues.append(
                        f"Actor '{actor_name}' teleported between shots "
                        f"{i - 1} and {i} (distance: {distance:.2f})"
                    )

        # Check for impossible camera positions
        for i, camera in enumerate(self._cameras):
            if camera.position.y < -1:
                issues.append(
                    f"Shot {i}: Camera underground (y={camera.position.y:.2f})"
                )
            if camera.position.y > 100:
                issues.append(
                    f"Shot {i}: Camera unrealistically high (y={camera.position.y:.2f})"
                )

        return issues

    def generate_spatial_prompt_additions(self) -> list[str]:
        """Generate spatial continuity additions for shot prompts."""
        additions: list[str] = []

        for i, shot in enumerate(self._shots):
            camera = shot["camera"]
            actors = shot["actors"]

            parts = [f"SPATIAL — Shot {i}:"]

            # Camera position description
            if camera.movement != "static":
                parts.append(
                    f"Camera at ({camera.position.x:.1f}, {camera.position.y:.1f}, "
                    f"{camera.position.z:.1f}), moving {camera.movement}"
                )
            else:
                parts.append(
                    f"Camera static at ({camera.position.x:.1f}, {camera.position.y:.1f}, "
                    f"{camera.position.z:.1f})"
                )

            # Actor positions
            for actor in actors:
                parts.append(
                    f"{actor.name} at ({actor.position.x:.1f}, {actor.position.y:.1f}, "
                    f"{actor.position.z:.1f}), {actor.action}, facing {actor.facing_direction}"
                )

            # Continuity note
            if i > 0:
                self._cameras[i - 1]
                movement = self.get_camera_movement_vector(i - 1, i)
                if movement and (abs(movement.x) > 0.1 or abs(movement.z) > 0.1):
                    parts.append(
                        "Camera moved from previous position — maintain spatial consistency"
                    )

            additions.append("\n".join(parts))

        return additions

    def get_report(self) -> dict[str, Any]:
        """Generate a spatial continuity report."""
        return {
            "total_shots": len(self._shots),
            "actors_tracked": list(self._actors.keys()),
            "180_rule_violations": self._180_rule_violations,
            "continuity_issues": self.validate_spatial_continuity(),
            "camera_positions": [
                cam.to_dict() for cam in self._cameras
            ],
        }


def create_spatial_tracker_from_shots(
    shot_prompts: list[str],
    subject: str = "subject",
) -> SpatialTracker:
    """Create a SpatialTracker from shot prompts with spatial hints.

    This is a convenience function that extracts spatial information
    from prompts and creates a basic tracker.
    """
    tracker = SpatialTracker()

    for i, prompt in enumerate(shot_prompts):
        # Extract camera position hints
        camera = CameraState()

        # Simple heuristics for camera position from prompt
        prompt_lower = prompt.lower()
        if "low angle" in prompt_lower:
            camera.position.y = -0.5
            camera.look_at.y = 1.0
        elif "high angle" in prompt_lower:
            camera.position.y = 3.0
            camera.look_at.y = 0.0
        elif "eye level" in prompt_lower:
            camera.position.y = 1.6

        if "wide shot" in prompt_lower or "establishing" in prompt_lower:
            camera.position.z = -8.0
            camera.focal_length_mm = 24.0
        elif "close-up" in prompt_lower:
            camera.position.z = -2.0
            camera.focal_length_mm = 85.0
        elif "medium shot" in prompt_lower:
            camera.position.z = -4.0
            camera.focal_length_mm = 50.0

        # Extract movement
        if "push in" in prompt_lower or "dolly in" in prompt_lower:
            camera.movement = "push_in"
        elif "pull out" in prompt_lower or "dolly out" in prompt_lower:
            camera.movement = "pull_out"
        elif "tracking" in prompt_lower:
            camera.movement = "tracking"
        elif "orbital" in prompt_lower:
            camera.movement = "orbital"
        else:
            camera.movement = "static"

        # Add actor
        actors = [ActorState(name=subject)]

        tracker.add_shot(i, camera, actors)

    return tracker

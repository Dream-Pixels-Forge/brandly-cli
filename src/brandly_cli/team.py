"""Team management and multi-user collaboration for Brandly projects."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Team constants
# ---------------------------------------------------------------------------


TEAM_ROLES = {
    "OWNER": "owner",
    "ADMIN": "admin",
    "EDITOR": "editor",
    "VIEWER": "viewer",
}

TEAM_ROLE_LABELS = {
    "OWNER": "Owner",
    "ADMIN": "Admin",
    "EDITOR": "Editor",
    "VIEWER": "Viewer",
}

TEAM_ROLE_PERMISSIONS = {
    "OWNER": ["manage_team", "manage_projects", "edit_projects"],
    "ADMIN": ["manage_team", "manage_projects", "edit_projects"],
    "EDITOR": ["edit_projects"],
    "VIEWER": [],
}


# ---------------------------------------------------------------------------
# Team models
# ---------------------------------------------------------------------------


class TeamMember(BaseModel):
    """A member of a Brandly team."""
    user_id: str = Field(..., description="Unique identifier for the user")
    username: str = Field(..., description="Display name or username")
    email: str | None = Field(None, description="Email address")
    role: str = Field(default="viewer", description="Role in the team")
    joined_at: str = Field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    is_active: bool = Field(default=True, description="Whether the member is active")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in TEAM_ROLES.values():
            raise ValueError(f"Role must be one of {list(TEAM_ROLES.values())}")
        return v

    def to_dict(self) -> dict[str, Any]:
        """Include unset fields with defaults so round-tripping preserves the full model shape."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeamMember:
        """Create a TeamMember from a dictionary."""
        return cls(**data)


class TeamInvitation(BaseModel):
    """An invitation to join a team."""
    invitation_id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    team_id: str = Field(..., description="Team the invitation is for")
    email: str = Field(..., description="Email address to invite")
    role: str = Field(default="viewer", description="Role to assign upon acceptance")
    invited_by: str = Field(..., description="User ID of the inviter")
    created_at: str = Field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    expires_at: str | None = Field(None, description="Expiration date for the invitation")
    is_accepted: bool = Field(default=False, description="Whether the invitation has been accepted")

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in TEAM_ROLES.values():
            raise ValueError(f"Role must be one of {list(TEAM_ROLES.values())}")
        return v

    def to_dict(self) -> dict[str, Any]:
        """Include unset fields with defaults so round-tripping preserves the full model shape."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeamInvitation:
        """Create a TeamInvitation from a dictionary."""
        return cls(**data)


class Team(BaseModel):
    """A Brandly team with members and shared projects."""
    team_id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex)
    name: str = Field(..., description="Team name")
    description: str | None = Field(None, description="Team description")
    owner_id: str = Field(..., description="User ID of the team owner")
    members: dict[str, TeamMember] = Field(default_factory=dict, description="Team members by user_id")
    projects: list[str] = Field(default_factory=list, description="Project IDs shared with the team")
    created_at: str = Field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    settings: dict[str, Any] = Field(default_factory=dict, description="Team-level settings")

    def add_member(self, user_id: str, username: str, role: str = "viewer", email: str | None = None) -> TeamMember:
        """Add a member to the team."""
        member = TeamMember(
            user_id=user_id,
            username=username,
            email=email,
            role=role
        )
        self.members[user_id] = member
        self.updated_at = __import__('datetime').datetime.now().isoformat()
        return member

    def remove_member(self, user_id: str) -> bool:
        """Remove a member from the team."""
        if user_id in self.members:
            del self.members[user_id]
            self.updated_at = __import__('datetime').datetime.now().isoformat()
            return True
        return False

    def update_member_role(self, user_id: str, role: str) -> bool:
        """Update a member's role."""
        if user_id in self.members:
            self.members[user_id].role = role
            self.updated_at = __import__('datetime').datetime.now().isoformat()
            return True
        return False

    def add_project(self, project_id: str) -> None:
        """Add a project to the team's shared projects."""
        if project_id not in self.projects:
            self.projects.append(project_id)
            self.updated_at = __import__('datetime').datetime.now().isoformat()

    def remove_project(self, project_id: str) -> bool:
        """Remove a project from the team's shared projects."""
        if project_id in self.projects:
            self.projects.remove(project_id)
            self.updated_at = __import__('datetime').datetime.now().isoformat()
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Include unset fields with defaults so round-tripping preserves the full model shape."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Team:
        """Create a Team from a dictionary."""
        return cls(**data)


# ---------------------------------------------------------------------------
# Team storage and management
# ---------------------------------------------------------------------------


def _get_teams_dir(root: Path | None = None) -> Path:
    """Get the directory where team data is stored."""
    base = Path(root) if root else Path.cwd()
    teams_dir = base / ".brandly" / "teams"
    teams_dir.mkdir(parents=True, exist_ok=True)
    return teams_dir


def _get_team_file(team_id: str, root: Path | None = None) -> Path:
    """Get the file path for a specific team."""
    return _get_teams_dir(root) / f"{team_id}.json"


#: Invitation ids are generated as ``uuid4().hex``. The charset is enforced so
#: an id can never escape the invitations directory (path traversal).
_INVITATION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _is_valid_invitation_id(invitation_id: str) -> bool:
    """Return True when the id is safe to use as a filename component."""
    return bool(_INVITATION_ID_RE.match(invitation_id))


def _get_invitations_dir(root: Path | None = None) -> Path:
    """Get the directory where team invitations are stored.

    Invitations live in a sub-directory of ``.brandly/teams/`` so the
    ``*.json`` glob used by :func:`list_teams_for_user` can never mistake an
    invitation for a team.
    """
    invitations_dir = _get_teams_dir(root) / "invitations"
    invitations_dir.mkdir(parents=True, exist_ok=True)
    return invitations_dir


async def save_invitation(invitation: TeamInvitation, root: Path | None = None) -> Path:
    """Save a team invitation to disk."""
    if not _is_valid_invitation_id(invitation.invitation_id):
        raise ValueError(f"Invalid invitation id: {invitation.invitation_id!r}")
    invitation_file = _get_invitations_dir(root) / f"{invitation.invitation_id}.json"
    invitation_file.write_text(
        json.dumps(invitation.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    return invitation_file


async def load_invitation(invitation_id: str, root: Path | None = None) -> TeamInvitation | None:
    """Load a team invitation by ID, or None when it does not exist."""
    if not _is_valid_invitation_id(invitation_id):
        return None
    invitation_file = _get_invitations_dir(root) / f"{invitation_id}.json"
    if not invitation_file.exists():
        return None
    try:
        data = json.loads(invitation_file.read_text(encoding="utf-8"))
        return TeamInvitation.from_dict(data)
    except Exception:
        return None


async def create_team(
    name: str,
    owner_id: str,
    owner_username: str,
    description: str | None = None,
    root: Path | None = None,
) -> Team:
    """Create a new team."""
    team = Team(
        name=name,
        description=description,
        owner_id=owner_id,
    )
    # Add the owner as the first member with OWNER role
    team.add_member(
        user_id=owner_id,
        username=owner_username,
        role="owner",
    )
    await save_team(team, root=root)
    return team


async def load_team(team_id: str, root: Path | None = None) -> Team | None:
    """Load a team by ID."""
    team_file = _get_team_file(team_id, root)
    if not team_file.exists():
        return None

    try:
        data = json.loads(team_file.read_text(encoding="utf-8"))
        return Team.from_dict(data)
    except Exception:
        return None


async def save_team(team: Team, root: Path | None = None) -> Path:
    """Save a team to disk."""
    team.updated_at = __import__('datetime').datetime.now().isoformat()
    team_file = _get_team_file(team.team_id, root)
    team_file.write_text(
        json.dumps(team.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    return team_file


async def delete_team(team_id: str, root: Path | None = None) -> bool:
    """Delete a team."""
    team_file = _get_team_file(team_id, root)
    if team_file.exists():
        team_file.unlink()
        return True
    return False


async def list_teams_for_user(user_id: str, root: Path | None = None) -> list[Team]:
    """List all teams a user is a member of."""
    teams_dir = _get_teams_dir(root)
    teams = []

    for team_file in teams_dir.glob("*.json"):
        team = await load_team(team_file.stem, root=root)
        if team and user_id in team.members:
            teams.append(team)

    return teams


async def invite_to_team(
    team_id: str,
    email: str,
    role: str,
    invited_by: str,
    root: Path | None = None,
    expires_days: int = 7,
) -> TeamInvitation:
    """Create a team invitation."""
    from datetime import datetime, timedelta

    team = await load_team(team_id, root=root)
    if not team:
        raise ValueError(f"Team {team_id} not found")

    # Check if inviter has permission to invite (OWNER or ADMIN)
    inviter = team.members.get(invited_by)
    if not inviter or inviter.role not in ["owner", "admin"]:
        raise PermissionError("Only owners and admins can send invitations")

    invitation = TeamInvitation(
        team_id=team_id,
        email=email,
        role=role,
        invited_by=invited_by,
        expires_at=(datetime.now() + timedelta(days=expires_days)).isoformat() if expires_days else None,
    )

    # The invitation is persisted so it can be accepted later. No mail service
    # is wired — the caller shares the invitation id.
    await save_invitation(invitation, root=root)
    return invitation


async def accept_invitation(
    invitation_id: str,
    user_id: str,
    username: str,
    root: Path | None = None,
) -> Team:
    """Accept a team invitation and add the invitee to the team.

    Raises:
        ValueError: when the invitation is unknown, malformed, already
            accepted, expired, or its team no longer exists.
    """
    if not _is_valid_invitation_id(invitation_id):
        raise ValueError(f"Invalid invitation id: {invitation_id!r}")

    invitation = await load_invitation(invitation_id, root=root)
    if invitation is None:
        raise ValueError(f"Invitation not found: {invitation_id}")
    if invitation.is_accepted:
        raise ValueError(f"Invitation already accepted: {invitation_id}")
    if invitation.expires_at:
        from datetime import datetime
        try:
            expires_at = datetime.fromisoformat(invitation.expires_at)
        except ValueError:
            # A corrupt expiry cannot be trusted — fail closed.
            raise ValueError(f"Invitation expired: {invitation_id}") from None
        if expires_at < datetime.now():
            raise ValueError(f"Invitation expired: {invitation_id}")

    team_obj = await load_team(invitation.team_id, root=root)
    if team_obj is None:
        raise ValueError(f"Team not found: {invitation.team_id}")

    team_obj.add_member(
        user_id=user_id,
        username=username,
        role=invitation.role,
        email=invitation.email,
    )
    invitation.is_accepted = True
    await save_invitation(invitation, root=root)
    await save_team(team_obj, root=root)
    return team_obj


# ---------------------------------------------------------------------------
# Team utility functions
# ---------------------------------------------------------------------------


def get_user_role_in_team(team: Team, user_id: str) -> str | None:
    """Get a user's role in a team, or None if not a member."""
    member = team.members.get(user_id)
    return member.role if member else None


def user_can_edit_project(team: Team, user_id: str) -> bool:
    """Check if a user can edit projects in a team."""
    role = get_user_role_in_team(team, user_id)
    return role in ["owner", "admin", "editor"]


def user_can_manage_team(team: Team, user_id: str) -> bool:
    """Check if a user can manage team membership and settings."""
    role = get_user_role_in_team(team, user_id)
    return role in ["owner", "admin"]


def user_can_owner_team(team: Team, user_id: str) -> bool:
    """Check if a user is the owner of the team."""
    role = get_user_role_in_team(team, user_id)
    return role == "owner"


async def get_team_projects(team_id: str, root: Path | None = None) -> list[str]:
    """Get list of project IDs shared with a team."""
    team = await load_team(team_id, root=root)
    return team.projects if team else []


async def add_project_to_team(
    team_id: str,
    project_id: str,
    root: Path | None = None,
) -> bool:
    """Add a project to a team's shared projects."""
    team = await load_team(team_id, root=root)
    if not team:
        return False

    team.add_project(project_id)
    await save_team(team, root=root)
    return True


async def remove_project_from_team(
    team_id: str,
    project_id: str,
    root: Path | None = None,
) -> bool:
    """Remove a project from a team's shared projects."""
    team = await load_team(team_id, root=root)
    if not team:
        return False

    result = team.remove_project(project_id)
    if result:
        await save_team(team, root=root)
    return result

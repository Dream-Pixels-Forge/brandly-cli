"""Tests for team invitations — creation, persistence and acceptance.

Covers the invite -> accept round trip that was previously a no-op:
``brandly team invite`` printed "Invitation sent" but persisted nothing, and
``brandly team accept`` printed "Would accept ..." while doing nothing.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from brandly_cli import team
from brandly_cli.cli import cli


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


def _make_team(tmp_path: Path, owner: str = "owner123") -> team.Team:
    return _run(team.create_team(
        name="Test Team",
        owner_id=owner,
        owner_username="owner",
        root=tmp_path,
    ))


def _current_user_id() -> str:
    """The user id the CLI derives from the system user."""
    import getpass
    return f"user_{getpass.getuser().replace(' ', '_').lower()}"


def _make_cli_team(tmp_path: Path) -> team.Team:
    """A team owned by the current system user (the CLI checks permissions)."""
    return _run(team.create_team(
        name="Test Team",
        owner_id=_current_user_id(),
        owner_username="owner",
        root=tmp_path,
    ))


def _invite(tmp_path: Path, team_obj: team.Team, **kwargs) -> team.TeamInvitation:
    params: dict = {
        "team_id": team_obj.team_id,
        "email": "invitee@example.com",
        "role": "editor",
        "invited_by": "owner123",
        "root": tmp_path,
        "expires_days": 7,
    }
    params.update(kwargs)
    return _run(team.invite_to_team(**params))


class TestInvitationPersistence:
    """The invitation must survive the call that created it."""

    def test_invitation_is_persisted(self, tmp_path: Path) -> None:
        """invite_to_team writes the invitation to disk."""
        team_obj = _make_team(tmp_path)
        invitation = _invite(tmp_path, team_obj)

        path = tmp_path / ".brandly" / "teams" / "invitations" / f"{invitation.invitation_id}.json"
        assert path.exists(), f"invitation not persisted at {path}"

    def test_invitation_round_trips(self, tmp_path: Path) -> None:
        """A persisted invitation loads back with every field intact."""
        team_obj = _make_team(tmp_path)
        invitation = _invite(tmp_path, team_obj)

        loaded = _run(team.load_invitation(invitation.invitation_id, root=tmp_path))
        assert loaded is not None
        assert loaded.invitation_id == invitation.invitation_id
        assert loaded.team_id == team_obj.team_id
        assert loaded.email == "invitee@example.com"
        assert loaded.role == "editor"
        assert loaded.invited_by == "owner123"
        assert loaded.is_accepted is False
        assert loaded.expires_at == invitation.expires_at

    def test_load_unknown_invitation_returns_none(self, tmp_path: Path) -> None:
        """An unknown id loads as None rather than raising."""
        assert _run(team.load_invitation("nope", root=tmp_path)) is None

    def test_invitations_are_not_listed_as_teams(self, tmp_path: Path) -> None:
        """An invitation file must never be mistaken for a team."""
        team_obj = _make_team(tmp_path)
        _invite(tmp_path, team_obj)

        teams = _run(team.list_teams_for_user("owner123", root=tmp_path))
        assert [t.team_id for t in teams] == [team_obj.team_id]


class TestAcceptInvitation:
    """accept_invitation must actually add the member."""

    def test_accept_adds_member_with_invitation_role(self, tmp_path: Path) -> None:
        """The invitee joins with the role and email from the invitation."""
        team_obj = _make_team(tmp_path)
        invitation = _invite(tmp_path, team_obj)

        accepted = _run(team.accept_invitation(
            invitation.invitation_id, "user456", "user456", root=tmp_path,
        ))

        assert "user456" in accepted.members
        member = accepted.members["user456"]
        assert member.role == "editor"
        assert member.email == "invitee@example.com"
        assert member.username == "user456"

    def test_accept_persists_the_team(self, tmp_path: Path) -> None:
        """The membership change is written to the team file."""
        team_obj = _make_team(tmp_path)
        invitation = _invite(tmp_path, team_obj)

        _run(team.accept_invitation(invitation.invitation_id, "user456", "u", root=tmp_path))

        reloaded = _run(team.load_team(team_obj.team_id, root=tmp_path))
        assert reloaded is not None
        assert "user456" in reloaded.members
        assert reloaded.members["user456"].role == "editor"

    def test_accept_marks_invitation_accepted(self, tmp_path: Path) -> None:
        """The invitation is marked accepted and that is persisted."""
        team_obj = _make_team(tmp_path)
        invitation = _invite(tmp_path, team_obj)

        _run(team.accept_invitation(invitation.invitation_id, "user456", "u", root=tmp_path))

        reloaded = _run(team.load_invitation(invitation.invitation_id, root=tmp_path))
        assert reloaded is not None
        assert reloaded.is_accepted is True

    def test_accept_unknown_invitation_raises(self, tmp_path: Path) -> None:
        """An unknown invitation id is an error, not a silent None."""
        with pytest.raises(ValueError, match="not found"):
            _run(team.accept_invitation("nope", "user456", "u", root=tmp_path))

    def test_accept_twice_raises(self, tmp_path: Path) -> None:
        """An invitation cannot be accepted twice."""
        team_obj = _make_team(tmp_path)
        invitation = _invite(tmp_path, team_obj)
        _run(team.accept_invitation(invitation.invitation_id, "user456", "u", root=tmp_path))

        with pytest.raises(ValueError, match="already accepted"):
            _run(team.accept_invitation(invitation.invitation_id, "user789", "u", root=tmp_path))

    def test_accept_expired_invitation_raises(self, tmp_path: Path) -> None:
        """An expired invitation is rejected."""
        team_obj = _make_team(tmp_path)
        invitation = _invite(tmp_path, team_obj, expires_days=7)

        expired = team.TeamInvitation(
            invitation_id=invitation.invitation_id,
            team_id=invitation.team_id,
            email=invitation.email,
            role=invitation.role,
            invited_by=invitation.invited_by,
            expires_at=(datetime.now() - timedelta(hours=1)).isoformat(),
        )
        _run(team.save_invitation(expired, root=tmp_path))

        with pytest.raises(ValueError, match="expired"):
            _run(team.accept_invitation(invitation.invitation_id, "user456", "u", root=tmp_path))

    def test_accept_missing_team_raises(self, tmp_path: Path) -> None:
        """An invitation whose team is gone is an error."""
        team_obj = _make_team(tmp_path)
        invitation = _invite(tmp_path, team_obj)
        _run(team.delete_team(team_obj.team_id, root=tmp_path))

        with pytest.raises(ValueError, match="Team not found"):
            _run(team.accept_invitation(invitation.invitation_id, "user456", "u", root=tmp_path))


class TestTeamAcceptCli:
    """The CLI must perform the acceptance, not describe it."""

    def test_accept_adds_member_and_exits_zero(self, tmp_path: Path) -> None:
        """`brandly team accept` joins the team for real."""
        team_obj = _make_cli_team(tmp_path)
        invitation = _run(team.invite_to_team(
            team_id=team_obj.team_id,
            email="invitee@example.com",
            role="editor",
            invited_by=_current_user_id(),
            root=tmp_path,
            expires_days=7,
        ))

        result = CliRunner().invoke(cli, [
            "team", "accept", invitation.invitation_id,
            "--username", "user456", "--root", str(tmp_path),
        ])

        assert result.exit_code == 0, result.output
        assert "accepted" in result.output.lower()
        reloaded = _run(team.load_team(team_obj.team_id, root=tmp_path))
        assert reloaded is not None
        assert "user_user456" in reloaded.members

    def test_accept_unknown_id_exits_one(self, tmp_path: Path) -> None:
        """An unknown invitation is a loud failure, never a false success."""
        result = CliRunner().invoke(cli, [
            "team", "accept", "nope", "--username", "user456", "--root", str(tmp_path),
        ])

        assert result.exit_code == 1, result.output
        assert "not found" in result.output.lower()


class TestTeamInviteCli:
    """The CLI must not claim to send an email."""

    def test_invite_says_created_not_sent(self, tmp_path: Path) -> None:
        """No mail service is wired — the command must not claim it sent one."""
        team_obj = _make_cli_team(tmp_path)

        result = CliRunner().invoke(cli, [
            "team", "invite", team_obj.team_id, "invitee@example.com",
            "--root", str(tmp_path),
        ])

        assert result.exit_code == 0, result.output
        # The command must not claim it delivered an email. The honest wording
        # ("No email is sent") does contain "sent", so assert on the claim.
        assert "invitation sent" not in result.output.lower()
        assert "created" in result.output.lower()

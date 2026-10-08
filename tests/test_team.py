"""Tests for team module — multi-user collaboration."""

from __future__ import annotations

import asyncio
from pathlib import Path

from brandly_cli import team


def _run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


class TestTeamModels:
    """Tests for team data models."""

    def test_team_role_validation(self) -> None:
        """Team role validation works correctly."""
        # Valid roles should work
        for role in team.TEAM_ROLES.values():
            member = team.TeamMember(
                user_id="test-user",
                username="testuser",
                role=role
            )
            assert member.role == role

        # Invalid role should raise ValueError
        try:
            team.TeamMember(
                user_id="test-user",
                username="testuser",
                role="invalid-role"
            )
            raise AssertionError("Should have raised ValueError")
        except ValueError:
            pass  # Expected

    def test_team_member_creation(self) -> None:
        """TeamMember creation works correctly."""
        member = team.TeamMember(
            user_id="user123",
            username="john_doe",
            email="john@example.com",
            role="editor"
        )
        assert member.user_id == "user123"
        assert member.username == "john_doe"
        assert member.email == "john@example.com"
        assert member.role == "editor"
        assert member.is_active is True
        assert member.joined_at is not None

    def test_team_creation(self) -> None:
        """Team creation works correctly."""
        team_obj = team.Team(
            name="Test Team",
            owner_id="owner123",
            description="A test team"
        )
        assert team_obj.name == "Test Team"
        assert team_obj.owner_id == "owner123"
        assert team_obj.description == "A test team"
        assert len(team_obj.members) == 0  # Owner not auto-added in model
        assert team_obj.projects == []

    def test_team_invitation(self) -> None:
        """TeamInvitation creation works correctly."""
        invitation = team.TeamInvitation(
            team_id="team123",
            email="invitee@example.com",
            role="viewer",
            invited_by="inviter123"
        )
        assert invitation.team_id == "team123"
        assert invitation.email == "invitee@example.com"
        assert invitation.role == "viewer"
        assert invitation.invited_by == "inviter123"
        assert invitation.is_accepted is False
        assert invitation.invitation_id is not None
        assert invitation.created_at is not None


class TestTeamFunctions:
    """Tests for team management functions."""

    def test_create_and_load_team(self, tmp_path: Path) -> None:
        """Creating and loading a team works correctly."""
        # Create team
        team_obj = _run(team.create_team(
            name="Test Team",
            owner_id="owner123",
            owner_username="owner",
            description="A test team",
            root=tmp_path
        ))

        assert team_obj.name == "Test Team"
        assert team_obj.owner_id == "owner123"
        assert team_obj.description == "A test team"
        assert team_obj.team_id is not None

        # Check that owner was added as member
        assert "owner123" in team_obj.members
        owner_member = team_obj.members["owner123"]
        assert owner_member.username == "owner"
        assert owner_member.role == "owner"

        # Load team
        loaded_team = _run(team.load_team(team_obj.team_id, root=tmp_path))
        assert loaded_team is not None
        assert loaded_team.team_id == team_obj.team_id
        assert loaded_team.name == "Test Team"
        assert loaded_team.owner_id == "owner123"
        assert "owner123" in loaded_team.members

    def test_team_member_operations(self, tmp_path: Path) -> None:
        """Team member add/update/remove operations work correctly."""
        # Create team
        team_obj = _run(team.create_team(
            name="Test Team",
            owner_id="owner123",
            owner_username="owner",
            root=tmp_path
        ))

        # Add a member
        member = team_obj.add_member(
            user_id="user456",
            username="user456",
            role="editor",
            email="user@example.com"
        )
        assert member.user_id == "user456"
        assert member.role == "editor"

        # Update member role
        result = team_obj.update_member_role("user456", "admin")
        assert result is True
        assert team_obj.members["user456"].role == "admin"

        # Remove member
        result = team_obj.remove_member("user456")
        assert result is True
        assert "user456" not in team_obj.members

        # Try to remove non-existent member
        result = team_obj.remove_member("nonexistent")
        assert result is False

    def test_team_project_operations(self, tmp_path: Path) -> None:
        """Team project add/remove operations work correctly."""
        # Create team
        team_obj = _run(team.create_team(
            name="Test Team",
            owner_id="owner123",
            owner_username="owner",
            root=tmp_path
        ))

        # Add projects
        team_obj.add_project("project1")
        team_obj.add_project("project2")
        assert len(team_obj.projects) == 2
        assert "project1" in team_obj.projects
        assert "project2" in team_obj.projects

        # Add duplicate project (should not duplicate)
        team_obj.add_project("project1")
        assert len(team_obj.projects) == 2

        # Remove project
        result = team_obj.remove_project("project1")
        assert result is True
        assert len(team_obj.projects) == 1
        assert "project2" in team_obj.projects

        # Try to remove non-existent project
        result = team_obj.remove_project("nonexistent")
        assert result is False

    def test_list_teams_for_user(self, tmp_path: Path) -> None:
        """Listing teams for a user works correctly."""
        # Create two teams
        team1 = _run(team.create_team(
            name="Team 1",
            owner_id="user1",
            owner_username="user1",
            root=tmp_path
        ))

        team2 = _run(team.create_team(
            name="Team 2",
            owner_id="user2",
            owner_username="user2",
            root=tmp_path
        ))

        # Add user1 to team2 as member
        team2_obj = _run(team.load_team(team2.team_id, root=tmp_path))
        team2_obj.add_member("user1", "user1", "viewer")
        _run(team.save_team(team2_obj, root=tmp_path))

        # List teams for user1
        user1_teams = _run(team.list_teams_for_user("user1", root=tmp_path))
        assert len(user1_teams) == 2

        team_ids = {t.team_id for t in user1_teams}
        assert team1.team_id in team_ids
        assert team2.team_id in team_ids

        # List teams for user2 (should only be in team2 as owner)
        user2_teams = _run(team.list_teams_for_user("user2", root=tmp_path))
        assert len(user2_teams) == 1
        assert user2_teams[0].team_id == team2.team_id

    def test_team_permission_functions(self, tmp_path: Path) -> None:
        """Team permission checking functions work correctly."""
        # Create team with different role members
        team_obj = _run(team.create_team(
            name="Test Team",
            owner_id="owner123",
            owner_username="owner",
            root=tmp_path
        ))

        # Add members with different roles
        team_obj.add_member("admin456", "admin", "admin")
        team_obj.add_member("editor789", "editor", "editor")
        team_obj.add_member("viewer000", "viewer", "viewer")

        # Test permission functions
        assert team.user_can_edit_project(team_obj, "owner123") is True
        assert team.user_can_edit_project(team_obj, "admin456") is True
        assert team.user_can_edit_project(team_obj, "editor789") is True
        assert team.user_can_edit_project(team_obj, "viewer000") is False

        assert team.user_can_manage_team(team_obj, "owner123") is True
        assert team.user_can_manage_team(team_obj, "admin456") is True
        assert team.user_can_manage_team(team_obj, "editor789") is False
        assert team.user_can_manage_team(team_obj, "viewer000") is False

        assert team.user_can_owner_team(team_obj, "owner123") is True
        assert team.user_can_owner_team(team_obj, "admin456") is False
        assert team.user_can_owner_team(team_obj, "editor789") is False
        assert team.user_can_owner_team(team_obj, "viewer000") is False

    def test_save_and_load_team(self, tmp_path: Path) -> None:
        """Saving and loading a team preserves all data."""
        # Create team with members and projects
        original_team = _run(team.create_team(
            name="Test Team",
            owner_id="owner123",
            owner_username="owner",
            description="A test team",
            root=tmp_path
        ))

        original_team.add_member("user456", "user", "editor", "user@example.com")
        original_team.add_project("project1")
        original_team.add_project("project2")

        # Save team
        saved_path = _run(team.save_team(original_team, root=tmp_path))
        assert saved_path.exists()

        # Load team
        loaded_team = _run(team.load_team(original_team.team_id, root=tmp_path))
        assert loaded_team is not None

        # Verify all data is preserved
        assert loaded_team.team_id == original_team.team_id
        assert loaded_team.name == original_team.name
        assert loaded_team.description == original_team.description
        assert loaded_team.owner_id == original_team.owner_id
        assert loaded_team.updated_at >= original_team.updated_at  # Updated during save

        # Check members
        assert len(loaded_team.members) == len(original_team.members)
        assert "owner123" in loaded_team.members
        assert "user456" in loaded_team.members
        assert loaded_team.members["owner123"].role == "owner"
        assert loaded_team.members["user456"].role == "editor"
        assert loaded_team.members["user456"].email == "user@example.com"

        # Check projects
        assert loaded_team.projects == original_team.projects
        assert "project1" in loaded_team.projects
        assert "project2" in loaded_team.projects

    def test_invite_to_team(self, tmp_path: Path) -> None:
        """Team invitation creation works correctly."""
        # Create team
        team_obj = _run(team.create_team(
            name="Test Team",
            owner_id="owner123",
            owner_username="owner",
            root=tmp_path
        ))

        # Create invitation
        invitation = _run(team.invite_to_team(
            team_id=team_obj.team_id,
            email="invitee@example.com",
            role="viewer",
            invited_by="owner123",
            root=tmp_path,
            expires_days=7
        ))

        assert invitation.team_id == team_obj.team_id
        assert invitation.email == "invitee@example.com"
        assert invitation.role == "viewer"
        assert invitation.invited_by == "owner123"
        assert invitation.is_accepted is False
        assert invitation.invitation_id is not None
        assert invitation.expires_at is not None

    def test_get_team_projects(self, tmp_path: Path) -> None:
        """Getting team projects works correctly."""
        # Create team and add projects
        team_obj = _run(team.create_team(
            name="Test Team",
            owner_id="owner123",
            owner_username="owner",
            root=tmp_path
        ))

        team_obj.add_project("project1")
        team_obj.add_project("project2")
        _run(team.save_team(team_obj, root=tmp_path))

        # Get projects
        projects = _run(team.get_team_projects(team_obj.team_id, root=tmp_path))
        assert projects == ["project1", "project2"]

    def test_add_remove_project_from_team(self, tmp_path: Path) -> None:
        """Adding/removing projects from team works correctly."""
        # Create team
        team_obj = _run(team.create_team(
            name="Test Team",
            owner_id="owner123",
            owner_username="owner",
            root=tmp_path
        ))

        # Add project
        result = _run(team.add_project_to_team(
            team_id=team_obj.team_id,
            project_id="project1",
            root=tmp_path
        ))
        assert result is True

        # Verify project was added
        team_after_add = _run(team.load_team(team_obj.team_id, root=tmp_path))
        assert "project1" in team_after_add.projects

        # Remove project
        result = _run(team.remove_project_from_team(
            team_id=team_obj.team_id,
            project_id="project1",
            root=tmp_path
        ))
        assert result is True

        # Verify project was removed
        team_after_remove = _run(team.load_team(team_obj.team_id, root=tmp_path))
        assert "project1" not in team_after_remove.projects

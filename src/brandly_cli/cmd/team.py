"""G8 PR 3/3: `brandly team` — team management and multi-user collaboration.

* `brandly team create` — create a new team
* `brandly team list` — list teams you're a member of
* `brandly team invite` — invite someone to a team
* `brandly team members` — list members of a team
* `brandly team role` — change a member's role
* `brandly team projects` — list projects shared with a team
* `brandly team add-project` — add a project to a team
* `brandly team remove-project` — remove a project from a team
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click

from brandly_cli import layout
from brandly_cli.cli import _get_root, console
from brandly_cli.team import (
    TEAM_ROLES,
    add_project_to_team,
    create_team,
    delete_team,
    get_user_role_in_team,
    invite_to_team,
    list_teams_for_user,
    load_team,
    remove_project_from_team,
    save_team,
    user_can_manage_team,
    user_can_owner_team,
)


def _resolve_team(ctx, team_id: str, root: str | None = None) -> tuple[Path, Path]:
    """Resolve team ID to team file path, validating permissions."""
    root_dir = Path(root) if root else _get_root(ctx)
    teams_dir = root_dir / ".brandly" / "teams"
    team_file = teams_dir / f"{team_id}.json"

    if not team_file.exists():
        console.print(f"[red]Team not found: {team_id}[/red]")
        sys.exit(1)

    return root_dir, team_file


@click.group("team")
def team_group() -> None:
    """G8: Team management and multi-user collaboration."""


@team_group.command("create")
@click.argument("name")
@click.option("--description", default="", help="Team description")
@click.option("--username", default=None, help="Your username (defaults to system user)")
@click.option("--root", default=None, help="Working directory")
def team_create(
    name: str,
    description: str,
    username: str | None,
    root: str | None,
) -> None:
    """Create a new team."""
    import getpass

    # Get username from option or system
    if username is None:
        username = getpass.getuser()

    # In a real implementation, we would get the user ID from auth/system
    # For now, we'll use a placeholder based on username
    owner_id = f"user_{username.replace(' ', '_').lower()}"

    team_obj = asyncio.run(create_team(
        name=name,
        owner_id=owner_id,
        owner_username=username,
        description=description if description else None,
        root=Path(root) if root else None,
    ))

    console.print(f"[green]✓ Team created:[/green] {team_obj.name}")
    console.print(f"  Team ID: [dim]{team_obj.team_id}[/dim]")
    console.print(f"  Your role: [bold]{TEAM_ROLES['OWNER']}[/bold]")
    console.print(f"  Invite others with: [code]brandly team invite {team_obj.team_id} <email>[/code]")


@team_group.command("list")
@click.option("--json", "json_out", is_flag=True, help="Emit machine-readable JSON")
@click.option("--root", default=None, help="Working directory")
def team_list(json_out: bool, root: str | None) -> None:
    """List teams you're a member of."""
    import getpass

    # Get username from system (in real implementation, this would come from auth)
    username = getpass.getuser()
    user_id = f"user_{username.replace(' ', '_').lower()}"

    teams = asyncio.run(list_teams_for_user(user_id, root=Path(root) if root else None))

    if json_out:
        team_data = []
        for t in teams:
            user_role = get_user_role_in_team(t, user_id)
            team_data.append({
                "team_id": t.team_id,
                "name": t.name,
                "description": t.description,
                "role": user_role,
                "member_count": len(t.members),
                "project_count": len(t.projects),
                "created_at": t.created_at,
            })
        print(json.dumps(team_data, indent=2, ensure_ascii=False))
        return

    if not teams:
        console.print("[yellow]You are not a member of any teams.[/yellow]")
        console.print("Create a team with: [code]brandly team create <name>[/code]")
        return

    from rich.table import Table

    table = Table(title="Your Teams")
    table.add_column("Team ID", style="dim")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Your Role", style="bold")
    table.add_column("Members", justify="right")
    table.add_column("Projects", justify="right")

    for team_obj in teams:
        user_role = get_user_role_in_team(team_obj, user_id)
        role_style = {
            "owner": "red",
            "admin": "yellow",
            "editor": "blue",
            "viewer": "green"
        }.get(user_role, "white")

        table.add_row(
            team_obj.team_id[:8] + "...",
            team_obj.name,
            team_obj.description or "",
            f"[{role_style}]{user_role}[/{role_style}]",
            str(len(team_obj.members)),
            str(len(team_obj.projects)),
        )

    console.print(table)


@team_group.command("invite")
@click.argument("team_id")
@click.argument("email")
@click.option(
    "--role",
    "role",
    default="viewer",
    show_default=True,
    type=click.Choice(list(TEAM_ROLES.values())),
)
@click.option("--expires-days", default=7, show_default=True, type=int)
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def team_invite(
    ctx: click.Context,
    team_id: str,
    email: str,
    role: str,
    expires_days: int,
    root: str | None,
) -> None:
    """Invite someone to join a team."""
    import getpass

    # Get current user info
    username = getpass.getuser()
    user_id = f"user_{username.replace(' ', '_').lower()}"

    # Resolve team and check permissions
    root_dir, team_file = _resolve_team(ctx, team_id, root)
    team_obj = asyncio.run(load_team(team_id, root=root_dir))

    if not user_can_manage_team(team_obj, user_id):
        console.print("[red]Permission denied: Only owners and admins can invite members[/red]")
        sys.exit(1)

    # Create invitation
    try:
        invitation = asyncio.run(invite_to_team(
            team_id=team_id,
            email=email,
            role=role,
            invited_by=user_id,
            root=root_dir,
            expires_days=expires_days,
        ))

        console.print(f"[green]✓ Invitation sent:[/green] {email}")
        console.print(f"  Role: [bold]{role}[/bold]")
        console.print(f"  Expires: {invitation.expires_at[:10] if invitation.expires_at else 'Never'}")
        console.print(f"  Invitation ID: [dim]{invitation.invitation_id}[/dim]")
        console.print(f"  Have them accept with: [code]brandly team accept {invitation.invitation_id}[/code]")

    except Exception as e:
        console.print(f"[red]Failed to send invitation:[/red] {e}")
        sys.exit(1)


@team_group.command("accept")
@click.argument("invitation_id")
@click.option("--username", default=None, help="Your username")
@click.option("--root", default=None, help="Working directory")
def team_accept(
    invitation_id: str,
    username: str | None,
    root: str | None,
) -> None:
    """Accept a team invitation."""
    import getpass

    # Get username from option or system
    if username is None:
        username = getpass.getuser()

    user_id = f"user_{username.replace(' ', '_').lower()}"

    # In a real implementation, we would load the invitation from storage
    # For this stub version, we'll simulate acceptance
    console.print("[yellow]Note: Invitation acceptance is a stub implementation.[/yellow]")
    console.print("In a full implementation, this would:")
    console.print("  1. Load the invitation from storage")
    console.print("  2. Validate it hasn't expired")
    console.print("  3. Add you to the team with the specified role")
    console.print("  4. Mark the invitation as accepted")
    console.print()
    console.print(f"Would accept invitation {invitation_id} for user {username} ({user_id})")


@team_group.command("members")
@click.argument("team_id")
@click.option("--json", "json_out", is_flag=True, help="Emit machine-readable JSON")
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def team_members(
    ctx: click.Context,
    team_id: str,
    json_out: bool,
    root: str | None,
) -> None:
    """List members of a team."""
    root_dir, team_file = _resolve_team(ctx, team_id, root)
    team_obj = asyncio.run(load_team(team_id, root=root_dir))

    if json_out:
        members_data = []
        for member in team_obj.members.values():
            members_data.append({
                "user_id": member.user_id,
                "username": member.username,
                "email": member.email,
                "role": member.role,
                "joined_at": member.joined_at,
                "is_active": member.is_active,
            })
        print(json.dumps(members_data, indent=2, ensure_ascii=False))
        return

    if not team_obj.members:
        console.print("[yellow]This team has no members.[/yellow]")
        return

    from rich.table import Table

    table = Table(title=f"Members of {team_obj.name}")
    table.add_column("User ID")
    table.add_column("Username")
    table.add_column("Email")
    table.add_column("Role", style="bold")
    table.add_column("Joined", style="dim")
    table.add_column("Active")

    for member in sorted(team_obj.members.values(), key=lambda m: m.joined_at):
        role_style = {
            "owner": "red",
            "admin": "yellow",
            "editor": "blue",
            "viewer": "green"
        }.get(member.role, "white")

        table.add_row(
            member.user_id,
            member.username,
            member.email or "",
            f"[{role_style}]{member.role}[/{role_style}]",
            member.joined_at[:10] if member.joined_at else "",
            "✓" if member.is_active else "✗",
        )

    console.print(table)


@team_group.command("role")
@click.argument("team_id")
@click.argument("user_id")
@click.argument("role")
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def team_role(
    ctx: click.Context,
    team_id: str,
    user_id: str,
    role: str,
    root: str | None,
) -> None:
    """Change a member's role in a team."""
    root_dir, team_file = _resolve_team(ctx, team_id, root)
    team_obj = asyncio.run(load_team(team_id, root=root_dir))

    # Get current user info for permission check
    import getpass
    username = getpass.getuser()
    current_user_id = f"user_{username.replace(' ', '_').lower()}"

    if not user_can_manage_team(team_obj, current_user_id):
        console.print("[red]Permission denied: Only owners and admins can change roles[/red]")
        sys.exit(1)

    # Validate role
    if role not in TEAM_ROLES.values():
        console.print(f"[red]Invalid role:[/red] {role}. Must be one of {list(TEAM_ROLES.values())}")
        sys.exit(1)

    # Check if user exists in team
    if user_id not in team_obj.members:
        console.print(f"[red]User not found in team:[/red] {user_id}")
        sys.exit(1)

    # Prevent self-demotion of owner
    if user_id == team_obj.owner_id and role != TEAM_ROLES["OWNER"]:
        console.print("[red]Cannot change the owner's role[/red]")
        sys.exit(1)

    # Update role
    old_role = team_obj.members[user_id].role
    team_obj.update_member_role(user_id, role)
    asyncio.run(save_team(team_obj, root=root_dir))

    console.print(f"[green]✓ Role updated:[/green] {user_id}")
    console.print(f"  {old_role} → [bold]{role}[/bold]")


@team_group.command("projects")
@click.argument("team_id")
@click.option("--json", "json_out", is_flag=True, help="Emit machine-readable JSON")
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def team_projects(
    ctx: click.Context,
    team_id: str,
    json_out: bool,
    root: str | None,
) -> None:
    """List projects shared with a team."""
    root_dir, team_file = _resolve_team(ctx, team_id, root)
    team_obj = asyncio.run(load_team(team_id, root=root_dir))

    if json_out:
        print(json.dumps({
            "team_id": team_obj.team_id,
            "team_name": team_obj.name,
            "projects": team_obj.projects,
            "project_count": len(team_obj.projects),
        }, indent=2, ensure_ascii=False))
        return

    if not team_obj.projects:
        console.print("[yellow]This team has no shared projects.[/yellow]")
        console.print("Add projects with: [code]brandly team add-project <team_id> <project_id>[/code]")
        return

    from rich.table import Table

    table = Table(title=f"Projects shared with {team_obj.name}")
    table.add_column("Project ID")
    table.add_column("Shared Since", style="dim")

    # In a full implementation, we would track when each project was added
    # For now, we just list the project IDs
    for project_id in team_obj.projects:
        table.add_row(project_id, "unknown")

    console.print(table)


@team_group.command("add-project")
@click.argument("team_id")
@click.argument("project_id")
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def team_add_project(
    ctx: click.Context,
    team_id: str,
    project_id: str,
    root: str | None,
) -> None:
    """Add a project to a team's shared projects."""
    root_dir, team_file = _resolve_team(ctx, team_id, root)
    team_obj = asyncio.run(load_team(team_id, root=root_dir))

    # Get current user info for permission check
    import getpass
    username = getpass.getuser()
    current_user_id = f"user_{username.replace(' ', '_').lower()}"

    if not user_can_manage_team(team_obj, current_user_id):
        console.print("[red]Permission denied: Only owners and admins can manage team projects[/red]")
        sys.exit(1)

    # Validate that the project exists
    try:
        proj_dir = layout.resolve_project_dir(root_dir, project_id)
        if not proj_dir.is_dir():
            console.print(f"[red]Project not found:[/red] {project_id}")
            sys.exit(1)
    except Exception:
        console.print(f"[red]Invalid project ID:[/red] {project_id}")
        sys.exit(1)

    # Add project to team
    result = asyncio.run(add_project_to_team(team_id, project_id, root=root_dir))
    if result:
        console.print(f"[green]✓ Project added to team:[/green] {project_id}")
        console.print(f"  Team: [bold]{team_obj.name}[/bold]")
    else:
        console.print(f"[yellow]Project already in team:[/yellow] {project_id}")


@team_group.command("remove-project")
@click.argument("team_id")
@click.argument("project_id")
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def team_remove_project(
    ctx: click.Context,
    team_id: str,
    project_id: str,
    root: str | None,
) -> None:
    """Remove a project from a team's shared projects."""
    root_dir, team_file = _resolve_team(ctx, team_id, root)
    team_obj = asyncio.run(load_team(team_id, root=root_dir))

    # Get current user info for permission check
    import getpass
    username = getpass.getuser()
    current_user_id = f"user_{username.replace(' ', '_').lower()}"

    if not user_can_manage_team(team_obj, current_user_id):
        console.print("[red]Permission denied: Only owners and admins can manage team projects[/red]")
        sys.exit(1)

    # Remove project from team
    result = asyncio.run(remove_project_from_team(team_id, project_id, root=root_dir))
    if result:
        console.print(f"[green]✓ Project removed from team:[/green] {project_id}")
        console.print(f"  Team: [bold]{team_obj.name}[/bold]")
    else:
        console.print(f"[yellow]Project not found in team:[/yellow] {project_id}")


@team_group.command("delete")
@click.argument("team_id")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
@click.option("--root", default=None, help="Working directory")
@click.pass_context
def team_delete(
    ctx: click.Context,
    team_id: str,
    yes: bool,
    root: str | None,
) -> None:
    """Delete a team."""
    root_dir, team_file = _resolve_team(ctx, team_id, root)
    team_obj = asyncio.run(load_team(team_id, root=root_dir))

    # Get current user info for permission check
    import getpass
    username = getpass.getuser()
    current_user_id = f"user_{username.replace(' ', '_').lower()}"

    if not user_can_owner_team(team_obj, current_user_id):
        console.print("[red]Permission denied: Only the team owner can delete the team[/red]")
        sys.exit(1)

    # Confirm deletion
    if not yes:
        console.print(f"[red]Are you sure you want to delete team '{team_obj.name}'?[/red]")
        console.print("This action cannot be undone.")
        if not click.confirm("Continue?"):
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    # Delete team
    result = asyncio.run(delete_team(team_id, root=root_dir))
    if result:
        console.print(f"[green]✓ Team deleted:[/green] {team_obj.name}")
    else:
        console.print("[red]Failed to delete team[/red]")
        sys.exit(1)


def register(cli) -> None:  # type: ignore[no-untyped-def]
    cli.add_command(team_group)

"""graphxploit projects command — manage the project registry."""

import click

from cli.console import (
    print_banner, print_success, print_error, print_info,
    print_warning, console, make_table,
)


@click.group(invoke_without_command=True)
@click.pass_context
def projects(ctx):
    """List, rename, or delete registered projects.

    \b
    Examples:
      graphxploit projects              # list all projects
      graphxploit projects list
      graphxploit projects rename <id> "New Name"
      graphxploit projects delete <id>
    """
    if ctx.invoked_subcommand is None:
        _show_project_list()


def _show_project_list():
    """Display all registered projects as a styled table."""
    from cli.project_registry import list_projects

    all_projects = list_projects()

    if not all_projects:
        print_info("No projects registered yet.")
        print_info('Run [accent]graphxploit analyze ./your-project[/accent] to register one.')
        return

    table = make_table(
        title="Registered Projects",
        columns=[
            ("#", "bold cyan"),
            ("ID", "dim"),
            ("Name", "bold white"),
            ("Path", "dim"),
            ("Files", "cyan"),
            ("Vertices", "cyan"),
            ("Edges", "cyan"),
            ("Last Analyzed", "dim"),
        ],
        rows=[
            [
                str(i),
                p["id"],
                p["name"],
                p["path"],
                str(p.get("files", "?")),
                str(p.get("vertices", "?")),
                str(p.get("edges", "?")),
                (p.get("last_analyzed", "n/a").split("T")[0]
                 if "T" in p.get("last_analyzed", "")
                 else p.get("last_analyzed", "n/a")),
            ]
            for i, p in enumerate(all_projects, 1)
        ],
    )
    console.print()
    console.print(table)
    console.print()
    console.print("  [muted]Manage:[/muted]  graphxploit projects rename <id> \"New Name\"")
    console.print("  [muted]        [/muted]  graphxploit projects delete <id>")
    console.print("  [muted]Visualize:[/muted] graphxploit visualize")
    console.print()


@projects.command("list")
def list_cmd():
    """List all registered projects."""
    _show_project_list()


@projects.command()
@click.argument("project_id")
@click.argument("new_name")
def rename(project_id: str, new_name: str):
    """Rename a registered project.

    \b
    Example:
      graphxploit projects rename a1b2c3d4 "My Cool App"
    """
    from cli.project_registry import rename_project

    result = rename_project(project_id, new_name)
    if result:
        print_success(f"Project renamed to [accent]{new_name}[/accent]")
    else:
        print_error(f"No project found with id '{project_id}'.")
        print_info("Run [accent]graphxploit projects[/accent] to see all IDs.")


@projects.command()
@click.argument("project_id")
@click.confirmation_option(prompt="Are you sure you want to delete this project?")
def delete(project_id: str):
    """Delete a project from the registry.

    This only removes the registry entry. Your source code is not touched.

    \b
    Example:
      graphxploit projects delete a1b2c3d4
    """
    from cli.project_registry import delete_project

    if delete_project(project_id):
        print_success("Project removed from registry.")
    else:
        print_error(f"No project found with id '{project_id}'.")
        print_info("Run [accent]graphxploit projects[/accent] to see all IDs.")

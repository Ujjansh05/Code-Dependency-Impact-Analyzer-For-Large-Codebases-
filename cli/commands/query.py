"""graphxploit query command — interactive chatbot with persistent sessions."""

import os

import click

from cli.console import (
    print_banner, print_success, print_error, print_info,
    print_warning, console, make_table, make_panel,
)


def _default_inference_mode() -> str:
    mode = os.getenv("OLLAMA_INFERENCE_MODE", "fast").strip().lower()
    return mode if mode in {"fast", "slow", "balanced"} else "fast"


@click.command()
@click.argument("question", required=False, default=None)
@click.option(
    "--depth", "-d", default=5, show_default=True,
    help="Maximum graph traversal depth.",
)
@click.option(
    "--no-ai", is_flag=True, default=False,
    help="Skip LLM explanation, show only graph results.",
)
@click.option(
    "--mode",
    type=click.Choice(["fast", "slow", "balanced"], case_sensitive=False),
    default=_default_inference_mode,
    show_default=True,
    help="LLM inference profile for AI explanation.",
)
@click.option(
    "--use-model", default=None,
    help="Model ID from the registry to use (defaults to active model).",
)
@click.option(
    "--session", "-s", "session_id", default=None,
    help="Resume a previous session by ID.",
)
@click.option(
    "--history", is_flag=True, default=False,
    help="Show all past sessions.",
)
def query(question, depth, no_ai, mode, use_model, session_id, history):
    """Run a natural language impact query.

    \b
    Run without arguments to start an interactive chat session:
      graphxploit query

    \b
    Run with a question for a single query:
      graphxploit query "What happens if I change the login function?"

    \b
    Resume a past session:
      graphxploit query --session <id>

    \b
    View past sessions:
      graphxploit query --history
    """
    print_banner()
    mode = mode.lower()

    # Activate specified model if given.
    if use_model:
        from llm.model_registry import set_active_model
        switched = set_active_model(use_model)
        if switched:
            print_info(f"Using model: [accent]{switched.name}[/accent]")
        else:
            print_warning(f"Model '{use_model}' not found. Using active model.")

    # Show history and exit.
    if history:
        _show_session_history()
        return

    # Resume or create a session.
    from cli.session_manager import load_session, create_session

    current_session = None
    if session_id:
        current_session = load_session(session_id)
        if current_session:
            print_success(f"Resumed session: [accent]{current_session.name}[/accent] ({current_session.query_count} queries)")
            _show_session_context(current_session)
        else:
            print_error(f"Session '{session_id}' not found.")
            print_info("Use [accent]graphxploit query --history[/accent] to see all sessions.")
            return

    if not current_session:
        current_session = create_session()
        print_info(f"New session started: [accent]{current_session.id}[/accent]")

    console.print()

    # If a question was given inline, execute it and then open the REPL.
    if question:
        _execute_query(
            question=question,
            depth=depth,
            no_ai=no_ai,
            mode=mode,
            session=current_session,
        )

    # Enter interactive REPL.
    _interactive_loop(
        session=current_session,
        depth=depth,
        no_ai=no_ai,
        mode=mode,
    )


# ── Interactive REPL ────────────────────────────────────────────


def _interactive_loop(session, depth, no_ai, mode):
    """Run the interactive query chatbot loop."""
    from cli.session_manager import save_session

    console.print("  [bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold cyan]")
    console.print("  [bold]Interactive Mode[/bold]  │  [muted]Type your impact queries below[/muted]")
    console.print()
    console.print("  [muted]Commands:[/muted]")
    console.print("    [cyan]/history[/cyan]     Show past queries in this session")
    console.print("    [cyan]/sessions[/cyan]    List all saved sessions")
    console.print("    [cyan]/switch[/cyan] [muted]<id>[/muted]  Switch to a different session")
    console.print("    [cyan]/new[/cyan]         Start a new session")
    console.print("    [cyan]/name[/cyan] [muted]<name>[/muted] Rename this session")
    console.print("    [cyan]/delete[/cyan]      Delete this session")
    console.print("    [cyan]/depth[/cyan] [muted]<n>[/muted]   Set traversal depth (current: {})".format(depth))
    console.print("    [cyan]/mode[/cyan] [muted]<m>[/muted]    Set inference mode (current: {})".format(mode))
    console.print("    [cyan]/exit[/cyan]        Exit the chatbot")
    console.print("  [bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold cyan]")
    console.print()

    while True:
        try:
            user_input = console.input("  [bold red]GraphXploit[/bold red] [bold cyan]>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            print_info("Session saved. Goodbye!")
            save_session(session)
            return

        if not user_input:
            continue

        # Handle slash commands.
        if user_input.startswith("/"):
            cmd_parts = user_input.split(maxsplit=1)
            cmd = cmd_parts[0].lower()
            cmd_arg = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""

            if cmd in ("/exit", "/quit", "/q"):
                print_info("Session saved. Goodbye!")
                save_session(session)
                return

            elif cmd == "/history":
                _show_session_context(session)
                continue

            elif cmd == "/sessions":
                _show_session_history()
                continue

            elif cmd == "/switch":
                if not cmd_arg:
                    print_error("Usage: /switch <session_id>")
                    continue
                from cli.session_manager import load_session
                new_session = load_session(cmd_arg)
                if new_session:
                    save_session(session)
                    session = new_session
                    print_success(f"Switched to: [accent]{session.name}[/accent] ({session.query_count} queries)")
                    _show_session_context(session)
                else:
                    print_error(f"Session '{cmd_arg}' not found.")
                continue

            elif cmd == "/new":
                from cli.session_manager import create_session
                save_session(session)
                session = create_session()
                print_success(f"New session: [accent]{session.id}[/accent]")
                continue

            elif cmd == "/name":
                if not cmd_arg:
                    print_error("Usage: /name <new name>")
                    continue
                session.name = cmd_arg
                save_session(session)
                print_success(f"Session renamed to: [accent]{cmd_arg}[/accent]")
                continue

            elif cmd == "/delete":
                from cli.session_manager import delete_session, create_session
                if click.confirm(f"  Delete session '{session.name}'?", default=False):
                    delete_session(session.id)
                    print_success("Session deleted.")
                    session = create_session()
                    print_info(f"New session: [accent]{session.id}[/accent]")
                continue

            elif cmd == "/depth":
                if cmd_arg:
                    try:
                        depth = int(cmd_arg)
                        print_success(f"Depth set to {depth}")
                    except ValueError:
                        print_error("Depth must be a number.")
                else:
                    print_info(f"Current depth: {depth}")
                continue

            elif cmd == "/mode":
                if cmd_arg and cmd_arg.lower() in {"fast", "slow", "balanced"}:
                    mode = cmd_arg.lower()
                    print_success(f"Mode set to: {mode}")
                else:
                    print_error("Mode must be: fast, slow, or balanced")
                continue

            else:
                print_warning(f"Unknown command: {cmd}")
                continue

        # It's a query — execute it.
        _execute_query(
            question=user_input,
            depth=depth,
            no_ai=no_ai,
            mode=mode,
            session=session,
        )


# ── Single Query Execution ──────────────────────────────────────


def _execute_query(question, depth, no_ai, mode, session):
    """Execute a single impact query and save it to the session."""
    from cli.session_manager import QueryEntry, save_session

    print_info(f"Query: [accent]{question}[/accent]\n")

    # Parse the target.
    try:
        from llm.query_parser import extract_target

        with console.status("[bold cyan]Extracting target …[/bold cyan]", spinner="dots"):
            parsed = extract_target(question)
        target = parsed["target"]
        target_type = parsed["type"]
        raw = parsed.get("raw", "")

        if target_type == "unknown":
            if isinstance(raw, str) and raw.startswith("[Error]"):
                print_error(f"Target extraction failed: {raw}")
                print_info("Check Ollama model availability with:  curl http://localhost:11434/api/tags")
            else:
                print_error(
                    "Could not identify a function or file from your question.\n"
                    "  Try being more specific, e.g.:\n"
                    '  \"What breaks if I change the authenticate function?\"'
                )
            console.print()
            return

        print_info(f"Identified target: [accent]{target}[/accent] (type: {target_type})")

    except ImportError:
        print_error("LLM module not available. Is Ollama running?")
        return

    # Run graph query.
    try:
        from graph.tigergraph_client import get_connection
        from graph.target_resolver import resolve_target_id

        with console.status("[bold cyan]Traversing dependency graph …[/bold cyan]", spinner="dots"):
            conn = get_connection()
            target_id = resolve_target_id(target=target, target_type=target_type)

            if target_type == "function":
                start_func = target_id or target
                results = conn.runInstalledQuery(
                    "impact_analysis",
                    params={"start_func": (start_func,), "max_depth": depth},
                )
            else:
                start_node = target_id or target
                start_node_type = "CodeFile" if target_type == "file" else "CodeFunction"
                results = conn.runInstalledQuery(
                    "hop_detection",
                    params={"start_node": (start_node, start_node_type), "num_hops": depth},
                )
            affected = _extract_affected_nodes(results)

    except (ConnectionError, OSError, RuntimeError) as e:
        print_error(f"Graph query failed: {e}")
        print_info("Make sure TigerGraph is running: graphxploit status")
        return

    if not affected:
        print_success(f"No downstream impact detected for '{target}'.")
        console.print(
            "  [muted]This function/file has no outgoing dependencies in the loaded graph.[/muted]"
        )
        # Save to session even if no results.
        entry = QueryEntry(
            question=question,
            target=target,
            target_type=target_type,
            affected=[],
            explanation="No downstream impact detected.",
            risk="None",
        )
        session.add_entry(entry)
        save_session(session)
        console.print()
        return

    node_names = [n.split("::")[-1] if "::" in n else n for n in affected]

    table = make_table(
        title=f"Impact Analysis — {target}",
        columns=[
            ("#", "dim"),
            ("Affected Component", "bold yellow"),
            ("Type", "cyan"),
        ],
        rows=[
            [
                str(i + 1),
                name,
                "Function" if n.startswith("func::") else "File",
            ]
            for i, (n, name) in enumerate(zip(affected, node_names))
        ],
    )
    console.print(table)

    # Risk assessment.
    console.print()
    risk = "Low" if len(affected) <= 2 else "Medium" if len(affected) <= 5 else "High"
    console.print(f"  Risk Level:  {risk}  ({len(affected)} components affected)")

    explanation = ""
    if not no_ai:
        console.print()
        print_info(f"Generating AI explanation ... (mode: {mode})")

        try:
            from llm.explainer import explain_impact
            from rich.panel import Panel

            with console.status("[bold cyan]Generating AI explanation …[/bold cyan]", spinner="dots"):
                explanation = explain_impact(question, target, node_names, mode=mode)
            console.print()
            console.print(Panel(explanation, title=" AI Explanation", border_style="blue"))
        except Exception as e:
            print_warning(f"AI explanation unavailable: {e}")
            print_info("Run with --no-ai to skip, or check Ollama: graphxploit status")

    # Save to session.
    entry = QueryEntry(
        question=question,
        target=target,
        target_type=target_type,
        affected=node_names,
        explanation=explanation,
        risk=risk,
    )
    session.add_entry(entry)
    save_session(session)

    console.print()


# ── Session Display Helpers ─────────────────────────────────────


def _show_session_context(session):
    """Show past queries in the current session."""
    if not session.entries:
        print_info("No queries in this session yet.")
        console.print()
        return

    console.print()
    console.print(f"  [bold cyan]Session:[/bold cyan] {session.name}  [muted](id: {session.id})[/muted]")
    console.print(f"  [muted]{session.query_count} queries  |  Created: {session.created_at.split('T')[0]}[/muted]")
    console.print()

    for i, entry in enumerate(session.entries, 1):
        ts = entry.timestamp.split("T")[0] if "T" in entry.timestamp else entry.timestamp
        risk_style = (
            "green" if entry.risk == "Low" or entry.risk == "None"
            else "yellow" if entry.risk == "Medium"
            else "red"
        )
        console.print(f"  [cyan]{i}.[/cyan]  [bold white]{entry.question}[/bold white]")
        console.print(f"     [muted]Target: {entry.target}  |  Affected: {len(entry.affected)}  |  Risk: [{risk_style}]{entry.risk}[/{risk_style}]  |  {ts}[/muted]")

    console.print()


def _show_session_history():
    """Show all saved sessions."""
    from cli.session_manager import list_sessions

    sessions = list_sessions()

    if not sessions:
        print_info("No saved sessions.")
        console.print("  [muted]Start a new one with:[/muted]  graphxploit query")
        console.print()
        return

    console.print()
    table = make_table(
        title="Saved Sessions",
        columns=[
            ("#", "dim"),
            ("ID", "cyan"),
            ("Name", "bold white"),
            ("Queries", "white"),
            ("Last Query", "white"),
            ("Updated", "dim"),
        ],
        rows=[
            [
                str(i),
                s.id,
                s.name[:30],
                str(s.query_count),
                (s.last_question[:40] + "...") if len(s.last_question) > 40 else s.last_question or "[muted]empty[/muted]",
                s.updated_at.split("T")[0] if "T" in s.updated_at else s.updated_at,
            ]
            for i, s in enumerate(sessions, 1)
        ],
    )
    console.print(table)
    console.print()
    console.print("  [muted]Resume a session:[/muted]  graphxploit query --session <id>")
    console.print("  [muted]Or in chat:[/muted]       /switch <id>")
    console.print()


# ── Graph Helpers ───────────────────────────────────────────────


def _extract_affected_nodes(results: list[dict] | None) -> list[str]:
    """Normalize installed-query outputs to a flat list of vertex IDs."""
    affected: list[str] = []
    if not results or not isinstance(results, list):
        return affected

    for rs in results:
        if "@@affected" in rs:
            raw_nodes = rs["@@affected"]
        elif "@@reachable" in rs:
            raw_nodes = rs["@@reachable"]
        else:
            continue

        for node in list(raw_nodes):
            if isinstance(node, str):
                affected.append(node)
            elif isinstance(node, dict):
                node_id = node.get("v_id") or node.get("id") or node.get("name")
                if node_id:
                    affected.append(str(node_id))
            else:
                affected.append(str(node))

    return affected

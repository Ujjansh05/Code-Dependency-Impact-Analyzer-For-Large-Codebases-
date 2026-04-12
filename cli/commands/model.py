"""graphxploit model command — mount, switch, test, and manage LLM models."""

import click

from cli.console import (
    print_banner, print_success, print_error, print_info,
    print_warning, console, make_table, make_panel,
)


@click.group(invoke_without_command=True)
@click.pass_context
def model(ctx):
    """Manage mounted LLM models.

    \b
    Examples:
      graphxploit model                     # list all mounted models
      graphxploit model mount               # interactive mount wizard
      graphxploit model mount --provider openai --api-key sk-... --model gpt-4o
      graphxploit model switch <id>         # set active model
      graphxploit model test                # validate active model
      graphxploit model info                # show detailed capabilities
      graphxploit model remove <id>         # unmount a model
    """
    if ctx.invoked_subcommand is None:
        _show_model_list()


def _show_model_list():
    """Display all registered models as a styled table."""
    from llm.model_registry import list_models

    all_models = list_models()

    if not all_models:
        print_info("No models mounted yet.")
        console.print()
        console.print("  [muted]Mount a model:[/muted]")
        console.print("    graphxploit model mount                                    [muted]# interactive wizard[/muted]")
        console.print("    graphxploit model mount --provider ollama --model qwen2.5-coder:7b")
        console.print("    graphxploit model mount --provider openai --api-key sk-... --model gpt-4o")
        console.print()
        return

    table = make_table(
        title="Mounted Models",
        columns=[
            ("#", "bold cyan"),
            ("ID", "dim"),
            ("Name", "bold white"),
            ("Provider", "cyan"),
            ("Model", "white"),
            ("Status", ""),
        ],
        rows=[
            [
                str(i),
                m.id,
                m.name,
                m.provider,
                _truncate(m.model_name, 24),
                "[bold green]● Active[/bold green]" if m.is_active else "[dim]○ Ready[/dim]",
            ]
            for i, m in enumerate(all_models, 1)
        ],
    )
    console.print()
    console.print(table)
    console.print()
    console.print("  [muted]Switch:[/muted]  graphxploit model switch <id>")
    console.print("  [muted]Test:[/muted]    graphxploit model test")
    console.print("  [muted]Info:[/muted]    graphxploit model info")
    console.print("  [muted]Remove:[/muted]  graphxploit model remove <id>")
    console.print()


@model.command("list")
def list_cmd():
    """List all mounted models."""
    _show_model_list()


@model.command()
@click.option("--provider", "-p", type=click.Choice(["ollama", "openai", "huggingface", "custom"], case_sensitive=False), default=None, help="Model provider.")
@click.option("--api-key", "-k", default=None, help="API key for the provider.")
@click.option("--model-name", "--model", "-m", "model_name", default=None, help="Model name/identifier.")
@click.option("--base-url", "-u", default=None, help="Custom endpoint URL.")
@click.option("--name", "-n", default=None, help="Display name for this model.")
@click.option("--set-active/--no-set-active", default=True, show_default=True, help="Set as the active model after mounting.")
@click.option("--skip-test", is_flag=True, default=False, help="Skip the validation test after mounting.")
def mount(provider, api_key, model_name, base_url, name, set_active, skip_test):
    """Mount a new LLM model.

    Run without flags for an interactive wizard, or pass flags for non-interactive mode.

    \b
    Examples:
      graphxploit model mount
      graphxploit model mount --provider ollama --model llama3
      graphxploit model mount --provider openai --api-key sk-... --model gpt-4o
      graphxploit model mount --provider huggingface --api-key hf_... --model mistralai/Mistral-7B-Instruct-v0.3
      graphxploit model mount --provider custom --base-url http://localhost:5000/v1 --model my-model
    """
    print_banner()
    print_info("Mount a new model\n")

    # Interactive wizard if no provider given.
    if provider is None:
        provider = _interactive_provider_select()

    if provider is None:
        return

    # Get provider-specific defaults and prompt for missing fields.
    if provider == "ollama":
        base_url, model_name = _configure_ollama(base_url, model_name)
    elif provider == "openai":
        base_url, api_key, model_name = _configure_openai(base_url, api_key, model_name)
    elif provider == "huggingface":
        base_url, api_key, model_name = _configure_huggingface(base_url, api_key, model_name)
    elif provider == "custom":
        base_url, api_key, model_name = _configure_custom(base_url, api_key, model_name)

    if not model_name:
        print_error("Model name is required.")
        return

    if not name:
        name = f"{provider.capitalize()} ({model_name})"

    # Test the connection before saving.
    if not skip_test:
        console.print()
        print_info("Testing connection ...")
        from llm.adapters import create_adapter
        adapter = create_adapter(
            provider=provider,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
        )

        if not adapter.check_health():
            print_error("Could not connect to the model endpoint.")
            print_info("Check the URL, API key, and that the service is running.")
            if not click.confirm("  Mount anyway?", default=False):
                return
        else:
            print_success("Connected!")

            print_info("Running code analysis validation ...")
            from llm.auto_config import validate_model_for_code_analysis, probe_model
            passed, message = validate_model_for_code_analysis(adapter)
            if passed:
                print_success(message)
            else:
                print_warning(message)
                if not click.confirm("  Mount anyway?", default=True):
                    return

            caps = probe_model(adapter)
            print_info(f"Capabilities: {caps.context_window:,} context, speed={caps.estimated_speed}")

    # Register the model.
    from llm.model_registry import ModelConfig, register_model

    config = ModelConfig(
        provider=provider,
        base_url=base_url or "",
        api_key=api_key or "",
        model_name=model_name,
        name=name,
        is_active=set_active,
    )
    result = register_model(config)

    console.print()
    print_success(f'Model mounted as [accent]{result.name}[/accent] (id: {result.id})')

    if set_active:
        print_success(f'"{result.name}" is now the active model.')

    console.print()


@model.command()
@click.argument("model_id")
def switch(model_id):
    """Set a mounted model as the active model.

    \b
    Example:
      graphxploit model switch a3f8c1d2
    """
    from llm.model_registry import set_active_model

    result = set_active_model(model_id)
    if result:
        print_success(f'Active model switched to [accent]{result.name}[/accent] ({result.provider} / {result.model_name})')
    else:
        print_error(f"No model found with id '{model_id}'.")
        print_info("Run [accent]graphxploit model[/accent] to see all IDs.")


@model.command()
@click.argument("model_id", required=False, default=None)
def test(model_id):
    """Test a model to validate it works for code analysis.

    Tests the active model if no ID is given.

    \b
    Examples:
      graphxploit model test
      graphxploit model test a3f8c1d2
    """
    print_banner()

    from llm.model_registry import get_active_config, get_model

    if model_id:
        config = get_model(model_id)
        if not config:
            print_error(f"No model found with id '{model_id}'.")
            return
    else:
        config = get_active_config()
        if not config:
            print_error("No active model. Mount one first with 'graphxploit model mount'.")
            return

    print_info(f'Testing model [accent]{config.name}[/accent] ({config.provider} / {config.model_name}) ...\n')

    from llm.adapters import create_adapter
    from llm.auto_config import run_full_probe

    adapter = create_adapter(
        provider=config.provider,
        base_url=config.base_url or None,
        model_name=config.model_name or None,
        api_key=config.api_key or None,
    )

    results = run_full_probe(adapter)

    if not results["healthy"]:
        print_error(f"Connection:      FAILED — {results['validation_message']}")
        return

    print_success("Connection:      OK")

    if results["validation_passed"]:
        print_success(f"Code extraction: OK — {results['validation_message']}")
    else:
        print_warning(f"Code extraction: WARN — {results['validation_message']}")

    caps = results.get("capabilities", {})
    if caps:
        ctx = caps.get("context_window", "?")
        speed = caps.get("estimated_speed", "?")
        print_success(f"Context window:  {ctx:,} tokens" if isinstance(ctx, int) else f"Context window:  {ctx}")
        print_success(f"Speed:           {speed}")

    console.print()
    if results["validation_passed"]:
        print_success("All tests passed. Model is ready for code impact analysis.")
    else:
        print_warning("Model may not perform optimally for code analysis. Consider a code-focused model.")

    console.print()


@model.command()
@click.argument("model_id", required=False, default=None)
def info(model_id):
    """Show detailed info and capabilities for a model.

    Shows the active model if no ID is given.

    \b
    Examples:
      graphxploit model info
      graphxploit model info a3f8c1d2
    """
    from llm.model_registry import get_active_config, get_model

    if model_id:
        config = get_model(model_id)
        if not config:
            print_error(f"No model found with id '{model_id}'.")
            return
    else:
        config = get_active_config()
        if not config:
            print_error("No active model.")
            return

    lines = [
        f"  [bold]ID:[/bold]              {config.id}",
        f"  [bold]Provider:[/bold]        {config.provider}",
        f"  [bold]Model:[/bold]           {config.model_name}",
        f"  [bold]Base URL:[/bold]        {config.base_url or '(default)'}",
        f"  [bold]API Key:[/bold]         {'●●●●●●●●' if config.api_key else '(none)'}",
        f"  [bold]Status:[/bold]          {'[green]● Active[/green]' if config.is_active else '[dim]○ Inactive[/dim]'}",
        f"  [bold]Mounted:[/bold]         {config.created_at.split('T')[0] if config.created_at and 'T' in config.created_at else config.created_at or 'n/a'}",
        f"  [bold]Last Used:[/bold]       {config.last_used.split('T')[0] if config.last_used and 'T' in config.last_used else config.last_used or 'never'}",
    ]

    if config.capabilities:
        caps = config.capabilities
        lines.append("")
        lines.append("  [bold cyan]Capabilities:[/bold cyan]")
        lines.append(f"    Context Window:  {caps.get('context_window', '?'):,}" if isinstance(caps.get('context_window'), int) else f"    Context Window:  {caps.get('context_window', '?')}")
        lines.append(f"    Speed:           {caps.get('estimated_speed', '?')}")
        lines.append(f"    Streaming:       {'Yes' if caps.get('supports_streaming') else 'No'}")
        lines.append(f"    JSON Mode:       {'Yes' if caps.get('supports_json_mode') else 'No'}")

    console.print()
    panel = make_panel("\n".join(lines), title=f"  {config.name}", style="cyan")
    console.print(panel)
    console.print()


@model.command()
@click.argument("model_id", required=False, default=None)
def probe(model_id):
    """Re-run auto-detection on a model to refresh its capabilities.

    \b
    Examples:
      graphxploit model probe
      graphxploit model probe a3f8c1d2
    """
    from llm.model_registry import get_active_config, get_model, update_model
    from llm.adapters import create_adapter
    from llm.auto_config import run_full_probe

    if model_id:
        config = get_model(model_id)
    else:
        config = get_active_config()

    if not config:
        print_error("No model found." if model_id else "No active model.")
        return

    print_info(f'Probing [accent]{config.name}[/accent] ...\n')

    adapter = create_adapter(
        provider=config.provider,
        base_url=config.base_url or None,
        model_name=config.model_name or None,
        api_key=config.api_key or None,
    )

    results = run_full_probe(adapter)

    if not results["healthy"]:
        print_error("Model is unreachable.")
        return

    # Save capabilities back to registry.
    if results["capabilities"]:
        update_model(config.id, capabilities=results["capabilities"])
        print_success("Capabilities updated in registry.")

    caps = results.get("capabilities", {})
    console.print(f"  Context Window:  {caps.get('context_window', '?')}")
    console.print(f"  Speed:           {caps.get('estimated_speed', '?')}")
    console.print(f"  Streaming:       {'Yes' if caps.get('supports_streaming') else 'No'}")

    if results["validation_passed"]:
        print_success(f"\n  Validation: {results['validation_message']}")
    else:
        print_warning(f"\n  Validation: {results['validation_message']}")

    console.print()


@model.command()
@click.argument("model_id")
@click.confirmation_option(prompt="Are you sure you want to remove this model?")
def remove(model_id):
    """Remove a mounted model from the registry.

    \b
    Example:
      graphxploit model remove a3f8c1d2
    """
    from llm.model_registry import delete_model

    if delete_model(model_id):
        print_success("Model removed from registry.")
    else:
        print_error(f"No model found with id '{model_id}'.")
        print_info("Run [accent]graphxploit model[/accent] to see all IDs.")


# ── Interactive helpers ─────────────────────────────────────────


def _interactive_provider_select() -> str | None:
    """Show an interactive provider picker."""
    console.print("  Select provider:\n")
    console.print("    [bold cyan]1)[/bold cyan]  Ollama [muted](local LLMs — llama3, qwen, mistral, etc.)[/muted]")
    console.print("    [bold cyan]2)[/bold cyan]  OpenAI [muted](GPT-4o, GPT-4o-mini, or any OpenAI-compatible API)[/muted]")
    console.print("    [bold cyan]3)[/bold cyan]  HuggingFace [muted](Inference API — any model on HF Hub)[/muted]")
    console.print("    [bold cyan]4)[/bold cyan]  Custom [muted](any endpoint with OpenAI-compatible /v1/chat/completions)[/muted]")
    console.print()

    choice = click.prompt("  Select", type=click.IntRange(1, 4))

    return {1: "ollama", 2: "openai", 3: "huggingface", 4: "custom"}[choice]


def _configure_ollama(base_url, model_name):
    """Configure Ollama-specific settings with full bootstrap support.

    Handles: install detection, auto-install, server startup,
    model availability check, and streaming pull with progress bar.
    """
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn
    from llm.ollama_setup import (
        is_ollama_installed, install_ollama,
        is_ollama_running, start_ollama_server,
        is_model_available, pull_model, list_local_models,
    )

    if not base_url:
        base_url = click.prompt("  Ollama URL", default="http://localhost:11434")

    # ── Step 1: Check if Ollama is installed ─────────────────────
    console.print()
    if is_ollama_installed():
        print_success("Ollama is installed")
    else:
        print_warning("Ollama is not installed.")
        if click.confirm("  Install Ollama now?", default=True):
            def _install_status(msg):
                print_info(msg)
            success = install_ollama(on_status=_install_status)
            if not success:
                print_error("Could not install Ollama automatically.")
                console.print("  [muted]Install manually: curl -fsSL https://ollama.com/install.sh | sh[/muted]")
                console.print("  [muted]Or visit: https://ollama.com[/muted]")
                console.print()
                return base_url, model_name
            print_success("Ollama installed!")
        else:
            print_info("Skipping Ollama installation.")
            console.print("  [muted]Install manually: curl -fsSL https://ollama.com/install.sh | sh[/muted]")
            console.print()
            return base_url, model_name

    # ── Step 2: Check if Ollama server is running ────────────────
    if is_ollama_running(base_url):
        print_success("Ollama server is running")
    else:
        print_info("Ollama server is not running. Starting it ...")
        def _start_status(msg):
            print_info(msg)
        success = start_ollama_server(
            base_url=base_url, on_status=_start_status, timeout=30
        )
        if success:
            print_success("Ollama server started!")
        else:
            print_error("Could not start Ollama server.")
            console.print("  [muted]Start manually: ollama serve[/muted]")
            console.print()
            return base_url, model_name

    # ── Step 3: List available models and prompt ─────────────────
    available = list_local_models(base_url)
    if available:
        console.print()
        console.print("  [bold cyan]Locally available models:[/bold cyan]")
        for i, m in enumerate(available[:15], 1):
            console.print(f"    [cyan]{i})[/cyan]  {m}")
        console.print()

    if not model_name:
        model_name = click.prompt("  Model name", default="qwen2.5-coder:7b")

    # ── Step 4: Check if model needs to be pulled ────────────────
    console.print()
    if is_model_available(model_name, base_url):
        print_success(f"Model '{model_name}' is already available locally")
    else:
        print_info(f"Model '{model_name}' is not available locally.")
        if click.confirm(f"  Pull '{model_name}' now?", default=True):
            console.print()

            # Use Rich progress bar for the download.
            with Progress(
                SpinnerColumn(style="cyan"),
                TextColumn("[bold cyan]{task.description}[/bold cyan]"),
                BarColumn(bar_width=40, style="red", complete_style="bold red", finished_style="bold green"),
                DownloadColumn(),
                TransferSpeedColumn(),
                console=console,
                transient=False,
            ) as progress:
                task_id = progress.add_task(f"  Pulling {model_name}", total=None)
                current_phase = {"text": ""}

                def _on_progress(status_text, completed, total):
                    if total > 0:
                        progress.update(task_id, total=total, completed=completed,
                                        description=f"  {status_text}")
                    current_phase["text"] = status_text

                def _on_status(msg):
                    progress.update(task_id, description=f"  {msg}")
                    current_phase["text"] = msg

                success = pull_model(
                    model_name=model_name,
                    base_url=base_url,
                    on_progress=_on_progress,
                    on_status=_on_status,
                )

            console.print()
            if success:
                print_success(f"Model '{model_name}' pulled successfully!")
            else:
                print_error(f"Failed to pull '{model_name}'.")
                console.print(f"  [muted]Try manually: ollama pull {model_name}[/muted]")
        else:
            print_info("Skipping model pull. You can pull it later:")
            console.print(f"  [muted]ollama pull {model_name}[/muted]")

    console.print()
    return base_url, model_name


def _configure_openai(base_url, api_key, model_name):
    """Configure OpenAI-specific settings."""
    if not base_url:
        base_url = click.prompt("  API base URL", default="https://api.openai.com/v1")
    if not api_key:
        api_key = click.prompt("  API key", hide_input=True)
    if not model_name:
        model_name = click.prompt("  Model name", default="gpt-4o-mini")
    return base_url, api_key, model_name


def _configure_huggingface(base_url, api_key, model_name):
    """Configure HuggingFace-specific settings."""
    if not base_url:
        base_url = click.prompt("  HF Inference URL", default="https://api-inference.huggingface.co/models")
    if not api_key:
        api_key = click.prompt("  HF API token", hide_input=True, default="")
    if not model_name:
        model_name = click.prompt("  Model ID", default="mistralai/Mistral-7B-Instruct-v0.3")
    return base_url, api_key, model_name


def _configure_custom(base_url, api_key, model_name):
    """Configure a custom endpoint."""
    if not base_url:
        base_url = click.prompt("  Endpoint URL (must be OpenAI-compatible)")
    if not api_key:
        api_key = click.prompt("  API key (leave blank if none)", default="", hide_input=True)
    if not model_name:
        model_name = click.prompt("  Model name")
    return base_url, api_key, model_name


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"

"""CLI commands for ReelCTL.

All user-facing commands are defined here using Typer. The CLI orchestrates
the full pipeline: scan → parse → AI → TMDB → plan → preview → execute.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.progress import Progress

from reelctl import __version__, setup_logging
from reelctl.config import load_settings
from reelctl.display import (
    confirm_execution,
    console,
    create_progress,
    show_banner,
    show_dry_run_notice,
    show_duplicates,
    show_execution_results,
    show_identifications,
    show_junk_files,
    show_operation_plan,
    show_scan_results,
    show_undo_results,
)

# ── App ────────────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="reelctl",
    help="🎬 ReelCTL — AI-Powered Media Organizer",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)


# ── Organize Command ──────────────────────────────────────────────────────────


@app.command()
def organize(
    path: Path = typer.Argument(
        ...,
        help="Directory to organize",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation and execute immediately",
    ),
    no_ai: bool = typer.Option(
        False,
        "--no-ai",
        help="Skip AI identification (use only local parsing)",
    ),
    no_verify: bool = typer.Option(
        False,
        "--no-verify",
        help="Skip TMDB verification",
    ),
) -> None:
    """🎬 Organize a media directory.

    Full pipeline: scan → parse → AI → TMDB → plan → preview → execute.
    Default mode is dry-run (preview only).
    """
    setup_logging()
    show_banner()
    settings = load_settings()

    # 1. Scan
    console.print("[bold cyan]Step 1/5:[/] Scanning directory...\n")
    from reelctl.scanner import scan_directory, find_associated_subtitles

    scan_result = scan_directory(path)
    show_scan_results(scan_result)

    if not scan_result.video_files:
        console.print("[warning]No video files found. Nothing to organize.[/]")
        raise typer.Exit()

    # 2. Parse + AI Identify
    console.print("[bold cyan]Step 2/5:[/] Identifying media...\n")
    identities = asyncio.run(
        _identify_media(scan_result, settings, use_ai=not no_ai, verify=not no_verify)
    )

    if not identities:
        console.print("[warning]Could not identify any media files.[/]")
        raise typer.Exit()

    show_identifications(identities)

    # 3. Detect junk & duplicates
    console.print("[bold cyan]Step 3/5:[/] Analyzing...\n")
    from reelctl.junk import detect_junk_files
    from reelctl.duplicates import detect_duplicates

    junk_files = detect_junk_files(scan_result.files)
    show_junk_files(junk_files)

    duplicate_groups = detect_duplicates(identities)
    show_duplicates(duplicate_groups)

    # 4. Build plan
    console.print("[bold cyan]Step 4/5:[/] Building operation plan...\n")
    from reelctl.planner import build_plan

    plan = build_plan(
        identities=identities,
        junk_files=junk_files,
        duplicate_groups=duplicate_groups,
        output_root=path,
        settings=settings,
    )
    show_operation_plan(plan)

    if plan.total_operations == 0:
        console.print("[success]Library is already organized! Nothing to do.[/]")
        raise typer.Exit()

    # 5. Execute
    if settings.dry_run and not yes:
        show_dry_run_notice()
        if not confirm_execution():
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit()

    console.print("[bold cyan]Step 5/5:[/] Executing...\n")
    from reelctl.operations import execute_plan
    from reelctl.undo import UndoManager

    undo_manager = UndoManager(base_dir=path / ".undo")

    progress = create_progress()
    with progress:
        success, failed = execute_plan(plan, undo_manager, progress)

    undo_manager.save(source_directory=path)
    show_execution_results(success, failed)


# ── Scan Command ──────────────────────────────────────────────────────────────


@app.command()
def scan(
    path: Path = typer.Argument(
        ...,
        help="Directory to scan",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
) -> None:
    """📂 Scan a directory and show file statistics."""
    setup_logging()
    show_banner()

    from reelctl.scanner import scan_directory

    result = scan_directory(path)
    show_scan_results(result)

    from reelctl.junk import detect_junk_files

    junk = detect_junk_files(result.files)
    show_junk_files(junk)


# ── Verify Command ─────────────────────────────────────────────────────────────


@app.command()
def verify(
    path: Path = typer.Argument(
        ...,
        help="Directory to verify",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
) -> None:
    """🔍 Identify media files without organizing."""
    setup_logging()
    show_banner()
    settings = load_settings()

    from reelctl.scanner import scan_directory

    scan_result = scan_directory(path)
    show_scan_results(scan_result)

    if not scan_result.video_files:
        console.print("[warning]No video files found.[/]")
        raise typer.Exit()

    identities = asyncio.run(_identify_media(scan_result, settings))
    show_identifications(identities)


# ── Undo Command ──────────────────────────────────────────────────────────────


@app.command()
def undo(
    path: Path = typer.Option(
        ".",
        "--path",
        "-p",
        help="Directory where .undo/ log is stored",
        resolve_path=True,
    ),
) -> None:
    """↩️  Undo the last organization."""
    setup_logging()
    show_banner()

    from reelctl.undo import undo_last

    undo_dir = Path(path) / ".undo"
    success, failed = undo_last(base_dir=undo_dir)

    if success == 0 and failed == 0:
        console.print("[warning]No undo log found in this directory.[/]")
    else:
        show_undo_results(success, failed)


# ── Clean Command ─────────────────────────────────────────────────────────────


@app.command()
def clean(
    path: Path = typer.Argument(
        ...,
        help="Directory to clean",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """🗑️  Detect and remove junk files."""
    setup_logging()
    show_banner()

    from reelctl.scanner import scan_directory
    from reelctl.junk import detect_junk_files

    result = scan_directory(path)
    junk = detect_junk_files(result.files)

    if not junk:
        console.print("[success]No junk files found! Directory is clean.[/]")
        raise typer.Exit()

    show_junk_files(junk)

    if not yes:
        if not confirm_execution():
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit()

    from send2trash import send2trash

    deleted = 0
    for jf in junk:
        try:
            send2trash(str(jf.path))
            deleted += 1
            console.print(f"  [error]✗[/] Deleted: {jf.name}")
        except Exception as e:
            console.print(f"  [error]Failed:[/] {jf.name} — {e}")

    console.print(f"\n[success]Cleaned {deleted}/{len(junk)} junk files.[/]")


# ── Doctor Command ─────────────────────────────────────────────────────────────


@app.command()
def doctor(
    path: Path = typer.Argument(
        ...,
        help="Directory to check",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
) -> None:
    """🩺 Check a media library for issues."""
    setup_logging()
    show_banner()
    settings = load_settings()

    from reelctl.scanner import scan_directory
    from reelctl.junk import detect_junk_files
    from reelctl.duplicates import detect_duplicates

    console.print("[bold]Running diagnostics...[/]\n")

    # Scan
    result = scan_directory(path)
    show_scan_results(result)

    issues = 0

    # Junk check
    junk = detect_junk_files(result.files)
    if junk:
        show_junk_files(junk)
        issues += len(junk)

    # Check for unorganized video files (not in proper folder structure)
    unorganized = []
    for vf in result.video_files:
        relative = vf.path.relative_to(path)
        parts = relative.parts
        # A properly organized file should be at least 2 levels deep
        # (e.g., Movies/Movie (Year)/file.mkv)
        if len(parts) < 2:
            unorganized.append(vf)

    if unorganized:
        console.print(f"[warning]⚠️  {len(unorganized)} video files not in organized folders:[/]")
        for uf in unorganized[:10]:
            console.print(f"  [dim]•[/] {uf.name}")
        if len(unorganized) > 10:
            console.print(f"  [dim]... and {len(unorganized) - 10} more[/]")
        console.print()
        issues += len(unorganized)

    # Identify and check for duplicates
    if result.video_files:
        identities = asyncio.run(_identify_media(result, settings, use_ai=False, verify=False))
        duplicates = detect_duplicates(identities)
        if duplicates:
            show_duplicates(duplicates)
            issues += len(duplicates)

    # Summary
    if issues == 0:
        console.print("[success]✓ No issues found! Library looks healthy.[/]")
    else:
        console.print(f"[warning]Found {issues} issue(s). Run 'reelctl organize' to fix.[/]")


# ── Config Command ─────────────────────────────────────────────────────────────


@app.command()
def config() -> None:
    """⚙️  Show current configuration."""
    setup_logging()
    show_banner()
    settings = load_settings()

    from rich.table import Table
    from rich import box

    table = Table(title="⚙️  Configuration", box=box.ROUNDED, border_style="dim")
    table.add_column("Setting", style="bold")
    table.add_column("Value", style="cyan")

    table.add_row("Groq API Key", "✓ Set" if settings.groq_api_key else "✗ Not set")
    table.add_row("TMDB API Key", "✓ Set" if settings.tmdb_api_key else "✗ Not set")
    table.add_row("TMDB Access Token", "✓ Set" if settings.tmdb_access_token else "✗ Not set")
    table.add_row("Language", settings.language)
    table.add_row("Movie Folder", settings.movie_folder)
    table.add_row("TV Folder", settings.tv_folder)
    table.add_row("Delete Junk", str(settings.delete_junk))
    table.add_row("Include Episode Title", str(settings.include_episode_title))
    table.add_row("Dry Run", str(settings.dry_run))
    table.add_row("AI Model", settings.groq_model)
    table.add_row("AI Confidence Threshold", f"{settings.ai_confidence_threshold:.0%}")
    table.add_row("AI Batch Size", str(settings.ai_batch_size))
    table.add_row("Cache TTL", f"{settings.cache_ttl_days} days")

    console.print(table)

    from reelctl.config import XDG_CONFIG_DIR

    console.print(f"\n  Config directory: [path]{XDG_CONFIG_DIR}[/]")


# ── Version Command ────────────────────────────────────────────────────────────


@app.command()
def version() -> None:
    """📌 Show version."""
    console.print(f"[bold cyan]ReelCTL[/] v{__version__}")


# ── Pipeline Helper ────────────────────────────────────────────────────────────


async def _identify_media(
    scan_result,
    settings,
    use_ai: bool = True,
    verify: bool = True,
) -> list:
    """Run the identification pipeline: parse → AI → TMDB.

    Args:
        scan_result: Results from scanning.
        settings: Application settings.
        use_ai: Whether to use AI identification.
        verify: Whether to verify against TMDB.

    Returns:
        List of MediaIdentity objects.
    """
    from reelctl.models import MediaIdentity, MediaType
    from reelctl.parser import parse_filename
    from reelctl.normalizer import normalize_quality, normalize_source
    from reelctl.scanner import find_associated_subtitles

    identities: list[MediaIdentity] = []
    video_files = scan_result.video_files
    all_subtitles = scan_result.subtitle_files

    # Step 1: Local parsing with guessit
    parsed_results = {}
    for vf in video_files:
        parsed = parse_filename(vf.name)
        parsed_results[vf.name] = parsed

    # Step 2: AI identification (if enabled)
    ai_results = {}
    if use_ai and settings.groq_api_key:
        from reelctl.ai import identify_media

        filenames = [vf.name for vf in video_files]
        ai_list = await identify_media(filenames, settings)
        for ai_result in ai_list:
            ai_results[ai_result.filename] = ai_result

    # Step 3: TMDB verification (if enabled)
    tmdb_client = None
    if verify and (settings.tmdb_api_key or settings.tmdb_access_token):
        from reelctl.cache import TMDBCache
        from reelctl.tmdb import TMDBClient

        cache = TMDBCache(ttl_days=settings.cache_ttl_days)
        tmdb_client = TMDBClient(settings, cache)

    # Step 4: Merge results for each video file
    for vf in video_files:
        parsed = parsed_results.get(vf.name)
        ai = ai_results.get(vf.name)

        # Determine best values — AI takes priority over local parsing
        if ai and ai.confidence >= settings.ai_confidence_threshold:
            media_type = ai.media_type
            title = ai.title
            year = ai.year
            season = ai.season
            episode = ai.episode
            quality = normalize_quality(ai.quality)
            source = normalize_source(ai.source)
            confidence = ai.confidence
        elif parsed and parsed.title:
            media_type = parsed.media_type
            title = parsed.title
            year = parsed.year
            season = parsed.season
            episode = parsed.episode
            quality = parsed.quality
            source = parsed.source
            confidence = 0.6  # Lower confidence for parser-only
        else:
            # Cannot identify
            continue

        # TMDB verification
        tmdb_id = None
        episode_name = None
        verified = False

        if tmdb_client:
            try:
                if media_type == MediaType.MOVIE:
                    tmdb_result = await tmdb_client.verify_movie(title, year)
                elif media_type == MediaType.TV:
                    tmdb_result = await tmdb_client.verify_tv(title, year, season, episode)
                else:
                    tmdb_result = None

                if tmdb_result:
                    title = tmdb_result.official_title
                    year = tmdb_result.year or year
                    tmdb_id = tmdb_result.tmdb_id
                    episode_name = tmdb_result.episode_name
                    verified = True
            except Exception as e:
                console.print(f"[dim]TMDB verification failed for '{title}': {e}[/]")

        # Find associated subtitles
        subs = find_associated_subtitles(vf, all_subtitles)

        identity = MediaIdentity(
            source_file=vf,
            media_type=media_type,
            title=title,
            year=year,
            season=season,
            episode=episode,
            episode_name=episode_name,
            quality=quality,
            source=source,
            tmdb_id=tmdb_id,
            confidence=confidence,
            verified=verified,
            associated_subtitles=subs,
        )
        identities.append(identity)

    return identities

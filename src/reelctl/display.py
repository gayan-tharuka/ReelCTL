"""Rich terminal UI for ReelCTL.

Beautiful, color-coded terminal output using the Rich library.
Provides summary tables, progress bars, and interactive prompts.
"""

from __future__ import annotations

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from reelctl.models import (
    DuplicateGroup,
    MediaIdentity,
    MediaType,
    OperationPlan,
    OperationType,
    ScanResult,
    ScannedFile,
)

# ── Theme ──────────────────────────────────────────────────────────────────────

REELCTL_THEME = Theme(
    {
        "info": "cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "movie": "bold magenta",
        "tv": "bold blue",
        "junk": "dim red",
        "path": "dim cyan",
        "quality": "bold yellow",
    }
)

console = Console(theme=REELCTL_THEME)


# ── Banner ─────────────────────────────────────────────────────────────────────


def show_banner() -> None:
    """Display the ReelCTL banner."""
    banner = Text()
    banner.append("  ____            _  ____ _____ _     \n", style="bold cyan")
    banner.append(" |  _ \\ ___  ___ | |/ ___|_   _| |    \n", style="bold cyan")
    banner.append(" | |_) / _ \\/ _ \\| | |     | | | |    \n", style="bold magenta")
    banner.append(" |  _ <  __/  __/| | |___  | | | |___ \n", style="bold magenta")
    banner.append(" |_| \\_\\___|\\___|_|_\\____| |_| |_____|\n", style="bold yellow")
    banner.append("                                       \n", style="dim")
    banner.append("  AI-Powered Media Organizer  v1.0.0", style="dim")

    console.print(Panel(banner, border_style="cyan", padding=(0, 2)))
    console.print()


# ── Scan Results ───────────────────────────────────────────────────────────────


def show_scan_results(result: ScanResult) -> None:
    """Display scan results in a summary table."""
    table = Table(
        title="📂 Scan Results",
        box=box.ROUNDED,
        title_style="bold cyan",
        border_style="dim",
    )

    table.add_column("Category", style="bold", min_width=12)
    table.add_column("Count", justify="right", style="cyan")
    table.add_column("Size", justify="right", style="dim")

    categories = [
        ("🎬 Video", result.video_files, "movie"),
        ("📝 Subtitle", result.subtitle_files, "info"),
        ("🖼️  Image", result.image_files, "dim"),
        ("🗑️  Junk", result.junk_files, "junk"),
        ("❓ Unknown", result.unknown_files, "warning"),
    ]

    for label, files, style in categories:
        size = sum(f.size_bytes for f in files)
        table.add_row(
            label,
            str(len(files)),
            _format_size(size),
            style=style,
        )

    table.add_section()
    table.add_row(
        "Total",
        str(len(result.files)),
        _format_size(result.total_size_bytes),
        style="bold",
    )

    console.print(table)
    console.print(f"  ⏱️  Scanned in [cyan]{result.scan_duration_seconds:.2f}s[/]")
    console.print()


# ── AI Results ─────────────────────────────────────────────────────────────────


def show_identifications(identities: list[MediaIdentity]) -> None:
    """Display AI identification results."""
    table = Table(
        title="🤖 Media Identification",
        box=box.ROUNDED,
        title_style="bold cyan",
        border_style="dim",
    )

    table.add_column("File", style="dim", max_width=35, no_wrap=True)
    table.add_column("Type", justify="center", min_width=6)
    table.add_column("Title", style="bold", min_width=20)
    table.add_column("Year", justify="center")
    table.add_column("Quality", justify="center", style="quality")
    table.add_column("Confidence", justify="center")
    table.add_column("Verified", justify="center")

    for ident in identities:
        # Type badge
        if ident.media_type == MediaType.MOVIE:
            type_badge = "[movie]🎬 Movie[/]"
        elif ident.media_type == MediaType.TV:
            ep_info = ""
            if ident.season and ident.episode:
                ep_info = f" S{ident.season:02d}E{ident.episode:02d}"
            type_badge = f"[tv]📺 TV{ep_info}[/]"
        else:
            type_badge = "[warning]❓ ???[/]"

        # Confidence indicator
        conf = ident.confidence
        if conf >= 0.95:
            conf_display = f"[success]●●●●● {conf:.0%}[/]"
        elif conf >= 0.80:
            conf_display = f"[info]●●●●○ {conf:.0%}[/]"
        elif conf >= 0.60:
            conf_display = f"[warning]●●●○○ {conf:.0%}[/]"
        else:
            conf_display = f"[error]●●○○○ {conf:.0%}[/]"

        # Verified badge
        verified = "[success]✓[/]" if ident.verified else "[warning]✗[/]"

        quality_display = ident.quality or ""
        if ident.source:
            quality_display += f" {ident.source}" if quality_display else ident.source

        table.add_row(
            ident.source_file.name,
            type_badge,
            ident.title,
            str(ident.year or ""),
            quality_display,
            conf_display,
            verified,
        )

    console.print(table)
    console.print()


# ── Operation Plan ─────────────────────────────────────────────────────────────


def show_operation_plan(plan: OperationPlan) -> None:
    """Display the operation plan preview."""
    if not plan.operations:
        console.print("[warning]No operations to perform.[/]")
        return

    # Summary panel
    summary_parts = []
    if plan.creates:
        summary_parts.append(f"[success]📁 {len(plan.creates)} folders[/]")
    if plan.moves:
        summary_parts.append(f"[info]📦 {len(plan.moves)} moves[/]")
    if plan.renames:
        summary_parts.append(f"[info]✏️  {len(plan.renames)} renames[/]")
    if plan.deletes:
        summary_parts.append(f"[error]🗑️  {len(plan.deletes)} deletes[/]")
    if plan.copies:
        summary_parts.append(f"[info]📋 {len(plan.copies)} copies[/]")

    summary_text = "  •  ".join(summary_parts)
    console.print(
        Panel(
            f"[bold]{plan.total_operations} operations ready[/]\n\n{summary_text}",
            title="📋 Operation Plan",
            border_style="cyan",
        )
    )

    # Operations table
    table = Table(box=box.SIMPLE, border_style="dim", show_header=True)
    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Operation", min_width=10)
    table.add_column("Source", style="path", max_width=40, no_wrap=True)
    table.add_column("→", justify="center", width=3)
    table.add_column("Destination", style="path", max_width=40, no_wrap=True)

    op_styles = {
        OperationType.CREATE_FOLDER: ("📁 Create", "success"),
        OperationType.MOVE_FILE: ("📦 Move", "info"),
        OperationType.RENAME_FILE: ("✏️  Rename", "info"),
        OperationType.DELETE_FILE: ("🗑️  Delete", "error"),
        OperationType.COPY_FILE: ("📋 Copy", "info"),
        OperationType.REMOVE_FOLDER: ("🗑️  Remove", "error"),
    }

    for i, op in enumerate(plan.operations, 1):
        label, style = op_styles.get(op.operation_type, ("?", "dim"))
        dest_display = str(op.destination.name) if op.destination else ""

        table.add_row(
            str(i),
            f"[{style}]{label}[/]",
            op.source.name,
            "→" if dest_display else "",
            dest_display,
        )

    console.print(table)
    console.print()


# ── Duplicates ─────────────────────────────────────────────────────────────────


def show_duplicates(groups: list[DuplicateGroup]) -> None:
    """Display duplicate detection results."""
    if not groups:
        return

    console.print(
        Panel(
            f"[warning]Found {len(groups)} duplicate group(s)[/]",
            title="🔍 Duplicate Detection",
            border_style="yellow",
        )
    )

    for group in groups:
        table = Table(
            title=f"  {group.title} ({group.year or '?'})",
            box=box.SIMPLE,
            title_style="bold",
        )
        table.add_column("Action", justify="center", width=8)
        table.add_column("File", min_width=30)
        table.add_column("Quality", justify="center")
        table.add_column("Size", justify="right")

        if group.recommended_keep:
            k = group.recommended_keep
            quality = f"{k.quality or '?'} {k.source or '?'}"
            table.add_row(
                "[success]✓ Keep[/]",
                k.source_file.name,
                f"[success]{quality}[/]",
                _format_size(k.source_file.size_bytes),
            )

        for dup in group.recommended_delete:
            quality = f"{dup.quality or '?'} {dup.source or '?'}"
            table.add_row(
                "[error]✗ Delete[/]",
                dup.source_file.name,
                f"[error]{quality}[/]",
                _format_size(dup.source_file.size_bytes),
            )

        console.print(table)

    console.print()


# ── Junk Files ─────────────────────────────────────────────────────────────────


def show_junk_files(junk_files: list[ScannedFile]) -> None:
    """Display detected junk files."""
    if not junk_files:
        return

    console.print(
        Panel(
            f"[junk]Found {len(junk_files)} junk file(s)[/]",
            title="🗑️  Junk Files",
            border_style="red",
        )
    )

    for jf in junk_files:
        console.print(f"  [junk]✗[/] {jf.name} [dim]({_format_size(jf.size_bytes)})[/]")

    console.print()


# ── Confirmation ───────────────────────────────────────────────────────────────


def confirm_execution() -> bool:
    """Ask user for confirmation before executing operations."""
    return Confirm.ask(
        "\n[bold]Proceed with execution?[/]",
        default=False,
        console=console,
    )


def show_dry_run_notice() -> None:
    """Show notice that this was a dry run."""
    console.print(
        Panel(
            "[warning]Nothing has been changed.[/]\n"
            "Run with [bold]--yes[/] to execute, or confirm when prompted.",
            title="ℹ️  Dry Run",
            border_style="yellow",
        )
    )


# ── Execution Results ──────────────────────────────────────────────────────────


def show_execution_results(success: int, failed: int) -> None:
    """Display execution results."""
    if failed == 0:
        console.print(
            Panel(
                f"[success]✓ All {success} operations completed successfully![/]",
                title="✅ Complete",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[warning]{success} succeeded, [error]{failed} failed[/]",
                title="⚠️  Partial Complete",
                border_style="yellow",
            )
        )
    console.print()


def show_undo_results(success: int, failed: int) -> None:
    """Display undo results."""
    if failed == 0:
        console.print(
            Panel(
                f"[success]✓ Successfully undone {success} operations![/]",
                title="↩️  Undo Complete",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[warning]{success} undone, [error]{failed} could not be reversed[/]",
                title="⚠️  Partial Undo",
                border_style="yellow",
            )
        )
    console.print()


# ── Progress Bar ───────────────────────────────────────────────────────────────


def create_progress() -> Progress:
    """Create a Rich progress bar for long operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────


def _format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"

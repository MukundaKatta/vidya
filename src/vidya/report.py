"""Rich progress reports for student learning."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from vidya.curriculum import Curriculum
from vidya.models import KnowledgeGap, MasteryLevel, TopicKnowledge
from vidya.student import Student
from vidya.tutor.spaced_repetition import SpacedRepetitionScheduler


_MASTERY_COLORS = {
    MasteryLevel.NOT_STARTED: "dim",
    MasteryLevel.NOVICE: "red",
    MasteryLevel.DEVELOPING: "yellow",
    MasteryLevel.PROFICIENT: "green",
    MasteryLevel.MASTERED: "bold green",
}

_MASTERY_SYMBOLS = {
    MasteryLevel.NOT_STARTED: "---",
    MasteryLevel.NOVICE: "*  ",
    MasteryLevel.DEVELOPING: "** ",
    MasteryLevel.PROFICIENT: "***",
    MasteryLevel.MASTERED: "***+",
}


def print_student_overview(
    student: Student,
    curriculum: Curriculum,
    console: Console | None = None,
) -> None:
    """Print a rich overview of a student's progress across a curriculum."""
    con = console or Console()

    # Header
    con.print()
    con.print(
        Panel(
            f"[bold]{student.name}[/bold]\n"
            f"Sessions: {student.model.total_sessions}  |  "
            f"Current Level: {student.current_difficulty.value}",
            title="Student Profile",
            border_style="blue",
        )
    )

    # Topic progress table
    table = Table(title=f"Progress: {curriculum.name}", show_lines=True)
    table.add_column("Topic", style="cyan", min_width=20)
    table.add_column("Mastery", justify="center", min_width=12)
    table.add_column("Score", justify="right", min_width=8)
    table.add_column("Attempts", justify="right", min_width=8)
    table.add_column("Accuracy", justify="right", min_width=8)
    table.add_column("Next Review", justify="center", min_width=14)

    for topic in curriculum.topics:
        tk = student.knowledge.get(topic.id)
        color = _MASTERY_COLORS.get(tk.mastery, "white")
        mastery_text = Text(tk.mastery.value.replace("_", " ").title(), style=color)

        score_text = f"{tk.score:.0%}"
        accuracy_text = f"{tk.accuracy:.0%}" if tk.attempts > 0 else "-"
        attempts_text = str(tk.attempts)

        if tk.next_review is not None:
            days_until = (tk.next_review - datetime.utcnow()).days
            if days_until <= 0:
                review_text = Text("DUE NOW", style="bold red")
            elif days_until == 1:
                review_text = Text("Tomorrow", style="yellow")
            else:
                review_text = Text(f"In {days_until} days", style="dim")
        else:
            review_text = Text("-", style="dim")

        table.add_row(
            topic.name,
            mastery_text,
            score_text,
            attempts_text,
            accuracy_text,
            review_text,
        )

    con.print(table)


def print_knowledge_gaps(
    gaps: list[KnowledgeGap],
    console: Console | None = None,
) -> None:
    """Print a report of knowledge gaps, ordered by priority."""
    con = console or Console()

    if not gaps:
        con.print(Panel("[green]No knowledge gaps detected![/green]", title="Knowledge Gaps"))
        return

    table = Table(title="Knowledge Gaps (by priority)", show_lines=True)
    table.add_column("Priority", justify="center", min_width=8)
    table.add_column("Topic", style="cyan", min_width=20)
    table.add_column("Score", justify="right", min_width=8)
    table.add_column("Target", justify="right", min_width=8)
    table.add_column("Severity", justify="center", min_width=10)
    table.add_column("Blocks", min_width=15)
    table.add_column("Recommendation", min_width=30)

    for gap in gaps:
        severity_pct = f"{gap.gap_severity:.0%}"
        if gap.gap_severity >= 0.7:
            severity_style = "bold red"
        elif gap.gap_severity >= 0.4:
            severity_style = "yellow"
        else:
            severity_style = "dim"

        blocks_text = ", ".join(gap.blocking_topics) if gap.blocking_topics else "-"

        table.add_row(
            str(gap.priority),
            gap.topic_name,
            f"{gap.current_score:.0%}",
            f"{gap.target_score:.0%}",
            Text(severity_pct, style=severity_style),
            blocks_text,
            gap.recommended_action,
        )

    con.print(table)


def print_spaced_repetition_stats(
    student: Student,
    scheduler: SpacedRepetitionScheduler,
    console: Console | None = None,
) -> None:
    """Print spaced repetition statistics for a student."""
    con = console or Console()
    stats = scheduler.stats(student.id)

    table = Table(title="Spaced Repetition Stats", show_lines=True)
    table.add_column("Metric", style="cyan", min_width=20)
    table.add_column("Value", justify="right", min_width=10)

    table.add_row("Total Cards", str(stats["total_cards"]))
    table.add_row("Due Now", Text(str(stats["due_now"]), style="bold red" if stats["due_now"] > 0 else "green"))
    table.add_row("Total Reviews", str(stats["total_reviews"]))
    table.add_row("Mature Cards (21+ days)", str(stats["mature_cards"]))
    table.add_row("Young Cards", str(stats["young_cards"]))
    table.add_row("New Cards", str(stats["new_cards"]))

    con.print(table)


def print_session_summary(
    questions_asked: int,
    questions_correct: int,
    topic_name: str,
    console: Console | None = None,
) -> None:
    """Print a summary of a completed learning session."""
    con = console or Console()
    accuracy = questions_correct / questions_asked if questions_asked > 0 else 0.0

    if accuracy >= 0.8:
        style = "bold green"
        verdict = "Excellent work!"
    elif accuracy >= 0.6:
        style = "yellow"
        verdict = "Good progress. Keep practicing."
    else:
        style = "bold red"
        verdict = "This topic needs more attention."

    panel_text = (
        f"Topic: [cyan]{topic_name}[/cyan]\n"
        f"Questions: {questions_asked}\n"
        f"Correct: {questions_correct}\n"
        f"Accuracy: [{style}]{accuracy:.0%}[/{style}]\n\n"
        f"[{style}]{verdict}[/{style}]"
    )

    con.print(Panel(panel_text, title="Session Summary", border_style="blue"))

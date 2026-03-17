"""Click CLI for Vidya: vidya teach, vidya assess, vidya practice."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from vidya.curriculum import Curriculum, Lesson, Topic
from vidya.models import DifficultyLevel, QuestionType
from vidya.report import print_knowledge_gaps, print_session_summary, print_student_overview
from vidya.student import Student
from vidya.tutor.difficulty_adapter import DifficultyAdapter
from vidya.tutor.gap_detector import GapDetector
from vidya.tutor.knowledge_assessor import KnowledgeAssessor
from vidya.tutor.lesson_generator import LessonGenerator
from vidya.tutor.spaced_repetition import SpacedRepetitionScheduler

console = Console()


def _build_demo_curriculum(subject: str, topic_name: str) -> tuple[Curriculum, Topic]:
    """Build a minimal curriculum from CLI arguments."""
    curriculum = Curriculum(name=f"{subject} Curriculum", subject=subject)
    topic = Topic(
        name=topic_name,
        description=f"Comprehensive coverage of {topic_name} within {subject}.",
        difficulty=DifficultyLevel.INTERMEDIATE,
    )
    curriculum.add_topic(topic)
    return curriculum, topic


@click.group()
@click.version_option(package_name="vidya")
def cli() -> None:
    """Vidya - AI Adaptive Tutoring Platform."""
    pass


@cli.command()
@click.option("--subject", required=True, help="Subject area (e.g., 'Python Programming').")
@click.option("--topic", required=True, help="Topic to teach (e.g., 'List Comprehensions').")
@click.option("--student", default="Student", help="Student name.")
@click.option(
    "--difficulty",
    type=click.Choice([d.value for d in DifficultyLevel]),
    default=DifficultyLevel.INTERMEDIATE.value,
    help="Starting difficulty level.",
)
def teach(subject: str, topic: str, student: str, difficulty: str) -> None:
    """Start an AI-powered teaching session on a topic."""
    diff = DifficultyLevel(difficulty)
    console.print(Panel(f"[bold blue]Vidya Teaching Session[/bold blue]\n\n"
                        f"Subject: {subject}\nTopic: {topic}\n"
                        f"Student: {student}\nDifficulty: {diff.value}",
                        border_style="blue"))

    curriculum, topic_obj = _build_demo_curriculum(subject, topic)
    student_obj = Student(name=student)
    student_obj.current_difficulty = diff

    console.print("\n[dim]Generating personalized lesson...[/dim]\n")

    generator = LessonGenerator()
    knowledge = student_obj.knowledge.get(topic_obj.id)

    lesson = generator.generate(
        topic=topic_obj,
        subject=subject,
        difficulty=diff,
        knowledge=knowledge,
    )

    console.print(Panel(f"[bold]{lesson.title}[/bold]", border_style="green"))
    console.print(lesson.content)

    if lesson.objectives:
        console.print("\n[bold cyan]Learning Objectives:[/bold cyan]")
        for i, obj in enumerate(lesson.objectives, 1):
            console.print(f"  {i}. {obj}")

    if lesson.examples:
        console.print("\n[bold cyan]Examples:[/bold cyan]")
        for i, ex in enumerate(lesson.examples, 1):
            console.print(f"\n[bold]Example {i}:[/bold]")
            console.print(f"  {ex}")

    if lesson.exercises:
        console.print("\n[bold cyan]Exercises:[/bold cyan]")
        for i, ex in enumerate(lesson.exercises, 1):
            console.print(f"\n[bold]Exercise {i}:[/bold]")
            console.print(f"  {ex}")


@cli.command()
@click.option("--subject", required=True, help="Subject area.")
@click.option("--topic", required=True, help="Topic to assess.")
@click.option("--student", default="Student", help="Student name.")
@click.option("--questions", default=5, help="Number of assessment questions.")
def assess(subject: str, topic: str, student: str, questions: int) -> None:
    """Assess knowledge on a topic with AI-generated questions."""
    console.print(Panel(f"[bold yellow]Knowledge Assessment[/bold yellow]\n\n"
                        f"Subject: {subject}\nTopic: {topic}\n"
                        f"Questions: {questions}",
                        border_style="yellow"))

    curriculum, topic_obj = _build_demo_curriculum(subject, topic)
    student_obj = Student(name=student)
    assessor = KnowledgeAssessor()
    adapter = DifficultyAdapter(initial_difficulty=student_obj.current_difficulty)

    console.print("\n[dim]Generating assessment questions...[/dim]\n")

    generated = assessor.generate_questions(
        topic=topic_obj,
        subject=subject,
        count=questions,
    )

    session = student_obj.start_session(topic_obj.id)
    correct_count = 0

    for i, q in enumerate(generated, 1):
        console.print(f"\n[bold]Question {i}/{len(generated)}:[/bold]")
        console.print(f"  {q.question}")

        if q.options:
            for j, opt in enumerate(q.options):
                label = chr(65 + j)  # A, B, C, D
                console.print(f"    {label}) {opt}")

        answer = Prompt.ask("\n[cyan]Your answer[/cyan]")
        result = assessor.evaluate_answer(topic_obj.name, q, answer)

        if result.is_correct:
            console.print(f"  [green]Correct![/green] (Score: {result.score:.0%})")
            correct_count += 1
        else:
            console.print(f"  [red]Incorrect.[/red] (Score: {result.score:.0%})")
            if q.explanation:
                console.print(f"  [dim]Explanation: {q.explanation}[/dim]")

        if result.feedback:
            console.print(f"  [dim]{result.feedback}[/dim]")

        student_obj.knowledge.update_from_result(
            topic_id=topic_obj.id,
            is_correct=result.is_correct,
            score=result.score,
        )
        adapter.record_performance(result.score)
        session.record_answer(result.is_correct)

    session.end()
    print_session_summary(len(generated), correct_count, topic, console)

    # Show gap analysis
    detector = GapDetector()
    gaps = detector.detect_gaps(student_obj, curriculum)
    if gaps:
        console.print()
        print_knowledge_gaps(gaps, console)

    print_student_overview(student_obj, curriculum, console)


@cli.command()
@click.option("--student", default="Student", help="Student name.")
@click.option("--subject", default="General", help="Subject area for review.")
def practice(student: str, subject: str) -> None:
    """Practice with spaced repetition review cards."""
    console.print(Panel(f"[bold magenta]Spaced Repetition Practice[/bold magenta]\n\n"
                        f"Student: {student}\nSubject: {subject}",
                        border_style="magenta"))

    student_obj = Student(name=student)
    scheduler = SpacedRepetitionScheduler()

    # Create sample review cards for demonstration
    sample_topics = [
        ("variables", "What is the difference between a local and global variable?",
         "A local variable is scoped to a function, while a global variable is accessible throughout the program."),
        ("functions", "What is a pure function?",
         "A function that always returns the same output for the same input and has no side effects."),
        ("loops", "When would you use a while loop instead of a for loop?",
         "When you don't know in advance how many iterations are needed."),
    ]

    for topic_id, question, answer in sample_topics:
        scheduler.create_card(
            student_id=student_obj.id,
            topic_id=topic_id,
            question=question,
            answer=answer,
        )

    due_cards = scheduler.get_due_cards(student_obj.id)

    if not due_cards:
        console.print("\n[green]No cards due for review right now![/green]")
        stats = scheduler.stats(student_obj.id)
        console.print(f"Total cards: {stats['total_cards']}")
        return

    console.print(f"\n[bold]Cards due for review: {len(due_cards)}[/bold]\n")

    for i, card in enumerate(due_cards, 1):
        console.print(f"[bold]Card {i}/{len(due_cards)}:[/bold]")
        console.print(f"  [cyan]{card.question}[/cyan]")

        Prompt.ask("\n[dim]Press Enter to reveal answer[/dim]")
        console.print(f"  [green]Answer: {card.answer}[/green]")

        rating = Prompt.ask(
            "\n[yellow]Rate your recall (1=forgot, 3=hard, 4=good, 5=easy)[/yellow]",
            choices=["1", "2", "3", "4", "5"],
            default="3",
        )

        score_map = {"1": 0.1, "2": 0.35, "3": 0.65, "4": 0.8, "5": 0.95}
        score = score_map[rating]
        scheduler.review_card(card, score)

        days = card.interval_days
        console.print(f"  [dim]Next review in {days} day{'s' if days != 1 else ''}[/dim]\n")

    console.print(Panel("[bold green]Practice session complete![/bold green]", border_style="green"))

    stats = scheduler.stats(student_obj.id)
    console.print(f"Total reviews: {stats['total_reviews']}")
    console.print(f"Cards remaining: {stats['due_now']}")


if __name__ == "__main__":
    cli()

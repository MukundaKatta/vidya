#!/usr/bin/env python3
"""Example: run a complete AI-powered tutoring session.

This script demonstrates the full Vidya workflow:
  1. Build a curriculum with topics and prerequisites
  2. Create a student and assess their knowledge
  3. Detect knowledge gaps
  4. Generate personalized lessons
  5. Track progress with spaced repetition

Requirements:
  - ANTHROPIC_API_KEY environment variable set
  - pip install -e .  (from the vidya project root)
"""

from __future__ import annotations

from rich.console import Console

from vidya.curriculum import Curriculum, Topic
from vidya.models import DifficultyLevel
from vidya.report import (
    print_knowledge_gaps,
    print_spaced_repetition_stats,
    print_student_overview,
)
from vidya.student import Student
from vidya.tutor.difficulty_adapter import DifficultyAdapter
from vidya.tutor.gap_detector import GapDetector
from vidya.tutor.knowledge_assessor import KnowledgeAssessor
from vidya.tutor.lesson_generator import LessonGenerator
from vidya.tutor.spaced_repetition import SpacedRepetitionScheduler

console = Console()


def build_python_curriculum() -> Curriculum:
    """Build a sample Python programming curriculum."""
    curriculum = Curriculum(
        name="Python Fundamentals",
        subject="Python Programming",
        description="A complete introduction to Python programming.",
    )

    variables = Topic(
        name="Variables and Data Types",
        description="Python variables, integers, floats, strings, booleans.",
        difficulty=DifficultyLevel.BEGINNER,
        keywords=["variables", "int", "float", "str", "bool", "type"],
        estimated_hours=2.0,
    )

    control_flow = Topic(
        name="Control Flow",
        description="If/else statements, for loops, while loops, break/continue.",
        prerequisites=[variables.id],
        difficulty=DifficultyLevel.BEGINNER,
        keywords=["if", "else", "for", "while", "break", "continue"],
        estimated_hours=3.0,
    )

    functions = Topic(
        name="Functions",
        description="Defining functions, parameters, return values, scope.",
        prerequisites=[variables.id, control_flow.id],
        difficulty=DifficultyLevel.ELEMENTARY,
        keywords=["def", "return", "parameters", "arguments", "scope"],
        estimated_hours=3.0,
    )

    data_structures = Topic(
        name="Data Structures",
        description="Lists, tuples, dictionaries, sets, and their operations.",
        prerequisites=[variables.id, control_flow.id],
        difficulty=DifficultyLevel.ELEMENTARY,
        keywords=["list", "tuple", "dict", "set", "comprehension"],
        estimated_hours=4.0,
    )

    oop = Topic(
        name="Object-Oriented Programming",
        description="Classes, objects, inheritance, polymorphism, encapsulation.",
        prerequisites=[functions.id, data_structures.id],
        difficulty=DifficultyLevel.INTERMEDIATE,
        keywords=["class", "object", "inheritance", "method", "self"],
        estimated_hours=5.0,
    )

    for topic in [variables, control_flow, functions, data_structures, oop]:
        curriculum.add_topic(topic)

    return curriculum


def run_session() -> None:
    """Run a complete tutoring session."""
    console.print("\n[bold blue]== Vidya AI Adaptive Tutoring Session ==[/bold blue]\n")

    # 1. Build curriculum
    curriculum = build_python_curriculum()
    console.print(f"Loaded curriculum: [cyan]{curriculum.name}[/cyan] "
                  f"({len(curriculum.topics)} topics)\n")

    # 2. Create student
    student = Student(name="Demo Student")
    console.print(f"Student: [cyan]{student.name}[/cyan]\n")

    # 3. Simulate some prior knowledge
    topics = curriculum.topics
    # Student knows variables well, struggles with control flow
    student.knowledge.update_from_result(topics[0].id, is_correct=True, score=0.9)
    student.knowledge.update_from_result(topics[0].id, is_correct=True, score=0.85)
    student.knowledge.update_from_result(topics[1].id, is_correct=False, score=0.3)
    student.knowledge.update_from_result(topics[1].id, is_correct=True, score=0.5)

    # 4. Detect knowledge gaps
    console.print("[bold]Analyzing knowledge gaps...[/bold]\n")
    detector = GapDetector(target_score=0.8)
    gaps = detector.detect_gaps(student, curriculum)
    print_knowledge_gaps(gaps, console)

    # 5. Set up difficulty adaptation
    adapter = DifficultyAdapter(
        initial_difficulty=student.current_difficulty,
        min_observations=3,
    )

    # 6. Set up spaced repetition
    scheduler = SpacedRepetitionScheduler()
    for topic in topics[:2]:
        scheduler.create_card(
            student_id=student.id,
            topic_id=topic.id,
            question=f"Explain the key concepts of {topic.name}.",
            answer=topic.description,
        )

    # 7. Show progress report
    console.print()
    print_student_overview(student, curriculum, console)
    console.print()
    print_spaced_repetition_stats(student, scheduler, console)

    # 8. Generate a lesson for the weakest topic (requires API key)
    if gaps:
        weakest = gaps[0]
        console.print(f"\n[bold]Generating lesson for: [cyan]{weakest.topic_name}[/cyan][/bold]\n")
        try:
            topic_obj = curriculum.get_topic(weakest.topic_id)
            if topic_obj:
                generator = LessonGenerator()
                knowledge = student.knowledge.get(weakest.topic_id)
                lesson = generator.generate(
                    topic=topic_obj,
                    subject=curriculum.subject,
                    difficulty=adapter.current_difficulty,
                    knowledge=knowledge,
                    gap_descriptions=[weakest.recommended_action],
                )
                console.print(f"[bold green]Lesson: {lesson.title}[/bold green]\n")
                console.print(lesson.content)
        except Exception as exc:
            console.print(f"[dim](Skipping AI lesson generation: {exc})[/dim]")

    console.print("\n[bold blue]== Session Complete ==[/bold blue]\n")


if __name__ == "__main__":
    run_session()

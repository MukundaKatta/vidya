"""Vidya tutor module: AI-powered adaptive tutoring components."""

from vidya.tutor.difficulty_adapter import DifficultyAdapter
from vidya.tutor.gap_detector import GapDetector
from vidya.tutor.knowledge_assessor import KnowledgeAssessor
from vidya.tutor.lesson_generator import LessonGenerator
from vidya.tutor.spaced_repetition import SpacedRepetitionScheduler

__all__ = [
    "DifficultyAdapter",
    "GapDetector",
    "KnowledgeAssessor",
    "LessonGenerator",
    "SpacedRepetitionScheduler",
]

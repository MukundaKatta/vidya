"""Core pydantic data models for Vidya."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DifficultyLevel(str, Enum):
    """Difficulty levels for content."""

    BEGINNER = "beginner"
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

    @property
    def numeric(self) -> int:
        return list(DifficultyLevel).index(self)

    @classmethod
    def from_numeric(cls, value: int) -> DifficultyLevel:
        levels = list(cls)
        clamped = max(0, min(value, len(levels) - 1))
        return levels[clamped]


class MasteryLevel(str, Enum):
    """How well a student has mastered a topic."""

    NOT_STARTED = "not_started"
    NOVICE = "novice"
    DEVELOPING = "developing"
    PROFICIENT = "proficient"
    MASTERED = "mastered"


class QuestionType(str, Enum):
    """Types of assessment questions."""

    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    CODE_EXERCISE = "code_exercise"
    EXPLANATION = "explanation"
    PROBLEM_SOLVING = "problem_solving"


class TopicModel(BaseModel):
    """A single topic within a curriculum."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    keywords: list[str] = Field(default_factory=list)
    estimated_hours: float = 1.0


class LessonModel(BaseModel):
    """A generated lesson for a student."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic_id: str
    title: str
    content: str
    difficulty: DifficultyLevel
    objectives: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    exercises: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CurriculumModel(BaseModel):
    """A full curriculum composed of topics."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    subject: str
    description: str = ""
    topics: list[TopicModel] = Field(default_factory=list)


class AssessmentQuestion(BaseModel):
    """A single assessment question."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic_id: str
    question: str
    question_type: QuestionType = QuestionType.SHORT_ANSWER
    options: list[str] = Field(default_factory=list)
    correct_answer: str = ""
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    explanation: str = ""


class AssessmentResult(BaseModel):
    """Result of answering an assessment question."""

    question_id: str
    topic_id: str
    student_answer: str
    is_correct: bool
    score: float = Field(ge=0.0, le=1.0)
    feedback: str = ""
    answered_at: datetime = Field(default_factory=datetime.utcnow)


class TopicKnowledge(BaseModel):
    """A student's knowledge state for a single topic."""

    topic_id: str
    mastery: MasteryLevel = MasteryLevel.NOT_STARTED
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    attempts: int = 0
    correct_count: int = 0
    last_assessed: Optional[datetime] = None
    last_practiced: Optional[datetime] = None

    # SM-2 spaced repetition fields
    easiness_factor: float = Field(default=2.5, ge=1.3)
    interval_days: int = 0
    repetition_number: int = 0
    next_review: Optional[datetime] = None

    @property
    def accuracy(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.correct_count / self.attempts


class KnowledgeGap(BaseModel):
    """An identified gap in student knowledge."""

    topic_id: str
    topic_name: str
    current_mastery: MasteryLevel
    current_score: float
    target_score: float = 0.8
    gap_severity: float = Field(ge=0.0, le=1.0)
    blocking_topics: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    priority: int = Field(default=0, ge=0)


class StudentModel(BaseModel):
    """A student profile."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    knowledge_state: dict[str, TopicKnowledge] = Field(default_factory=dict)
    current_difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    total_sessions: int = 0
    total_practice_minutes: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LearningSessionModel(BaseModel):
    """A single learning session."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    topic_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    questions_asked: int = 0
    questions_correct: int = 0
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    notes: str = ""

    @property
    def duration(self) -> Optional[timedelta]:
        if self.ended_at is None:
            return None
        return self.ended_at - self.started_at

    @property
    def accuracy(self) -> float:
        if self.questions_asked == 0:
            return 0.0
        return self.questions_correct / self.questions_asked


class SpacedRepetitionCard(BaseModel):
    """A review card for spaced repetition."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    topic_id: str
    question: str
    answer: str
    easiness_factor: float = Field(default=2.5, ge=1.3)
    interval_days: int = 0
    repetition_number: int = 0
    next_review: datetime = Field(default_factory=datetime.utcnow)
    last_reviewed: Optional[datetime] = None
    total_reviews: int = 0

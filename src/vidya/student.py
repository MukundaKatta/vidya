"""Student profile, knowledge state tracking, and learning sessions."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from vidya.models import (
    DifficultyLevel,
    KnowledgeGap,
    LearningSessionModel,
    MasteryLevel,
    StudentModel,
    TopicKnowledge,
)


def _mastery_from_score(score: float) -> MasteryLevel:
    """Derive mastery level from a numeric score."""
    if score >= 0.95:
        return MasteryLevel.MASTERED
    if score >= 0.75:
        return MasteryLevel.PROFICIENT
    if score >= 0.50:
        return MasteryLevel.DEVELOPING
    if score > 0.0:
        return MasteryLevel.NOVICE
    return MasteryLevel.NOT_STARTED


class KnowledgeState:
    """Tracks a student's knowledge across all topics."""

    def __init__(self, state: dict[str, TopicKnowledge] | None = None) -> None:
        self._state: dict[str, TopicKnowledge] = state or {}

    def get(self, topic_id: str) -> TopicKnowledge:
        """Get knowledge for a topic, creating a default entry if absent."""
        if topic_id not in self._state:
            self._state[topic_id] = TopicKnowledge(topic_id=topic_id)
        return self._state[topic_id]

    def update_from_result(
        self, topic_id: str, is_correct: bool, score: float
    ) -> TopicKnowledge:
        """Update knowledge state after an assessment result."""
        knowledge = self.get(topic_id)
        knowledge.attempts += 1
        if is_correct:
            knowledge.correct_count += 1
        # Exponential moving average for the score
        alpha = 0.3
        knowledge.score = alpha * score + (1 - alpha) * knowledge.score
        knowledge.mastery = _mastery_from_score(knowledge.score)
        knowledge.last_assessed = datetime.utcnow()
        return knowledge

    @property
    def all_topics(self) -> dict[str, TopicKnowledge]:
        return dict(self._state)

    def topics_due_for_review(self, as_of: datetime | None = None) -> list[str]:
        """Return topic IDs that are due for spaced-repetition review."""
        now = as_of or datetime.utcnow()
        due: list[str] = []
        for tid, tk in self._state.items():
            if tk.next_review is not None and tk.next_review <= now:
                due.append(tid)
        return due

    def weakest_topics(self, n: int = 5) -> list[TopicKnowledge]:
        """Return the n topics with the lowest scores (that have been attempted)."""
        attempted = [tk for tk in self._state.values() if tk.attempts > 0]
        attempted.sort(key=lambda tk: tk.score)
        return attempted[:n]


class LearningSession:
    """Manages a single learning session for a student on a topic."""

    def __init__(self, student_id: str, topic_id: str, difficulty: DifficultyLevel) -> None:
        self._model = LearningSessionModel(
            student_id=student_id,
            topic_id=topic_id,
            difficulty=difficulty,
        )

    @property
    def id(self) -> str:
        return self._model.id

    @property
    def model(self) -> LearningSessionModel:
        return self._model

    @property
    def accuracy(self) -> float:
        return self._model.accuracy

    def record_answer(self, is_correct: bool) -> None:
        """Record an answer during the session."""
        self._model.questions_asked += 1
        if is_correct:
            self._model.questions_correct += 1

    def end(self) -> LearningSessionModel:
        """End the session and return the final model."""
        self._model.ended_at = datetime.utcnow()
        return self._model


class Student:
    """A student with knowledge state and learning history."""

    def __init__(self, name: str, student_id: str | None = None) -> None:
        self._model = StudentModel(name=name)
        if student_id:
            self._model.id = student_id
        self.knowledge = KnowledgeState(self._model.knowledge_state)
        self._sessions: list[LearningSession] = []

    @property
    def id(self) -> str:
        return self._model.id

    @property
    def name(self) -> str:
        return self._model.name

    @property
    def current_difficulty(self) -> DifficultyLevel:
        return self._model.current_difficulty

    @current_difficulty.setter
    def current_difficulty(self, value: DifficultyLevel) -> None:
        self._model.current_difficulty = value

    @property
    def model(self) -> StudentModel:
        self._model.knowledge_state = self.knowledge.all_topics
        return self._model

    def start_session(
        self, topic_id: str, difficulty: DifficultyLevel | None = None
    ) -> LearningSession:
        """Begin a new learning session."""
        diff = difficulty or self.current_difficulty
        session = LearningSession(
            student_id=self.id,
            topic_id=topic_id,
            difficulty=diff,
        )
        self._sessions.append(session)
        self._model.total_sessions += 1
        return session

    def get_sessions(self, topic_id: str | None = None) -> list[LearningSession]:
        """Retrieve sessions, optionally filtered by topic."""
        if topic_id is None:
            return list(self._sessions)
        return [s for s in self._sessions if s.model.topic_id == topic_id]

    def __repr__(self) -> str:
        return f"Student(name={self.name!r}, id={self.id!r})"

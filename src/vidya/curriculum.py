"""Curriculum management: subjects, topics, and lesson organization."""

from __future__ import annotations

from vidya.models import (
    CurriculumModel,
    DifficultyLevel,
    LessonModel,
    TopicModel,
)


class Topic:
    """A single learning topic within a curriculum."""

    def __init__(
        self,
        name: str,
        description: str = "",
        prerequisites: list[str] | None = None,
        difficulty: DifficultyLevel = DifficultyLevel.BEGINNER,
        keywords: list[str] | None = None,
        estimated_hours: float = 1.0,
    ) -> None:
        self._model = TopicModel(
            name=name,
            description=description,
            prerequisites=prerequisites or [],
            difficulty=difficulty,
            keywords=keywords or [],
            estimated_hours=estimated_hours,
        )

    @property
    def id(self) -> str:
        return self._model.id

    @property
    def name(self) -> str:
        return self._model.name

    @property
    def description(self) -> str:
        return self._model.description

    @property
    def difficulty(self) -> DifficultyLevel:
        return self._model.difficulty

    @property
    def prerequisites(self) -> list[str]:
        return self._model.prerequisites

    @property
    def keywords(self) -> list[str]:
        return self._model.keywords

    @property
    def estimated_hours(self) -> float:
        return self._model.estimated_hours

    @property
    def model(self) -> TopicModel:
        return self._model

    def __repr__(self) -> str:
        return f"Topic(name={self.name!r}, difficulty={self.difficulty.value})"


class Lesson:
    """A generated lesson for a specific topic."""

    def __init__(
        self,
        topic_id: str,
        title: str,
        content: str,
        difficulty: DifficultyLevel,
        objectives: list[str] | None = None,
        examples: list[str] | None = None,
        exercises: list[str] | None = None,
    ) -> None:
        self._model = LessonModel(
            topic_id=topic_id,
            title=title,
            content=content,
            difficulty=difficulty,
            objectives=objectives or [],
            examples=examples or [],
            exercises=exercises or [],
        )

    @property
    def id(self) -> str:
        return self._model.id

    @property
    def topic_id(self) -> str:
        return self._model.topic_id

    @property
    def title(self) -> str:
        return self._model.title

    @property
    def content(self) -> str:
        return self._model.content

    @property
    def difficulty(self) -> DifficultyLevel:
        return self._model.difficulty

    @property
    def objectives(self) -> list[str]:
        return self._model.objectives

    @property
    def examples(self) -> list[str]:
        return self._model.examples

    @property
    def exercises(self) -> list[str]:
        return self._model.exercises

    @property
    def model(self) -> LessonModel:
        return self._model

    def __repr__(self) -> str:
        return f"Lesson(title={self.title!r}, difficulty={self.difficulty.value})"


class Curriculum:
    """A full curriculum composed of ordered topics."""

    def __init__(
        self,
        name: str,
        subject: str,
        description: str = "",
    ) -> None:
        self._model = CurriculumModel(
            name=name,
            subject=subject,
            description=description,
        )
        self._topics: dict[str, Topic] = {}

    @property
    def id(self) -> str:
        return self._model.id

    @property
    def name(self) -> str:
        return self._model.name

    @property
    def subject(self) -> str:
        return self._model.subject

    @property
    def topics(self) -> list[Topic]:
        return list(self._topics.values())

    @property
    def model(self) -> CurriculumModel:
        self._model.topics = [t.model for t in self._topics.values()]
        return self._model

    def add_topic(self, topic: Topic) -> None:
        """Add a topic to the curriculum."""
        self._topics[topic.id] = topic
        self._model.topics.append(topic.model)

    def get_topic(self, topic_id: str) -> Topic | None:
        """Retrieve a topic by ID."""
        return self._topics.get(topic_id)

    def get_topic_by_name(self, name: str) -> Topic | None:
        """Retrieve a topic by name (case-insensitive)."""
        lower = name.lower()
        for topic in self._topics.values():
            if topic.name.lower() == lower:
                return topic
        return None

    def get_prerequisites(self, topic_id: str) -> list[Topic]:
        """Get all prerequisite topics for a given topic."""
        topic = self._topics.get(topic_id)
        if topic is None:
            return []
        prereqs = []
        for pid in topic.prerequisites:
            prereq = self._topics.get(pid)
            if prereq is not None:
                prereqs.append(prereq)
        return prereqs

    def topological_order(self) -> list[Topic]:
        """Return topics in dependency-respecting order."""
        visited: set[str] = set()
        order: list[Topic] = []

        def visit(topic_id: str) -> None:
            if topic_id in visited:
                return
            visited.add(topic_id)
            topic = self._topics.get(topic_id)
            if topic is None:
                return
            for prereq_id in topic.prerequisites:
                visit(prereq_id)
            order.append(topic)

        for tid in self._topics:
            visit(tid)
        return order

    def __repr__(self) -> str:
        return (
            f"Curriculum(name={self.name!r}, subject={self.subject!r}, "
            f"topics={len(self._topics)})"
        )

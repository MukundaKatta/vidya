"""Generate personalized lessons from curriculum content using AI."""

from __future__ import annotations

import json
from typing import Optional

import anthropic

from vidya.curriculum import Lesson, Topic
from vidya.models import DifficultyLevel, MasteryLevel, TopicKnowledge


_LESSON_PROMPT = """\
You are an expert tutor creating a personalized lesson. Generate a structured lesson \
based on the following parameters.

Subject: {subject}
Topic: {topic_name}
Topic Description: {topic_description}
Target Difficulty: {difficulty}
Student's Current Mastery: {mastery}
Student's Current Score: {score:.0%}
Knowledge Gaps: {gaps}
Prerequisites Mastered: {prereqs_mastered}

Create a lesson that:
1. Starts from the student's current understanding level
2. Addresses identified knowledge gaps
3. Builds progressively toward the target difficulty
4. Includes concrete examples and practice exercises

Return a JSON object with:
- "title": a clear, descriptive lesson title
- "content": the full lesson text (use markdown formatting, be thorough)
- "objectives": array of 3-5 learning objectives
- "examples": array of 2-4 worked examples
- "exercises": array of 3-5 practice exercises (progressive difficulty)

Return ONLY the JSON object, no other text.
"""


class LessonGenerator:
    """Generates personalized lessons using AI based on student state."""

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self._client = client or anthropic.Anthropic()
        self._model = model

    def generate(
        self,
        topic: Topic,
        subject: str,
        difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
        knowledge: TopicKnowledge | None = None,
        gap_descriptions: list[str] | None = None,
        prerequisites_met: bool = True,
    ) -> Lesson:
        """Generate a personalized lesson for a topic.

        Args:
            topic: The topic to generate a lesson for.
            subject: The broader subject area.
            difficulty: Target difficulty level.
            knowledge: Student's current knowledge of this topic.
            gap_descriptions: Descriptions of relevant knowledge gaps.
            prerequisites_met: Whether the student has mastered prerequisites.

        Returns:
            A generated Lesson object.
        """
        mastery = knowledge.mastery.value if knowledge else MasteryLevel.NOT_STARTED.value
        score = knowledge.score if knowledge else 0.0
        gaps = "; ".join(gap_descriptions) if gap_descriptions else "None identified"

        prompt = _LESSON_PROMPT.format(
            subject=subject,
            topic_name=topic.name,
            topic_description=topic.description,
            difficulty=difficulty.value,
            mastery=mastery,
            score=score,
            gaps=gaps,
            prereqs_mastered="Yes" if prerequisites_met else "No - include review material",
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]

        lesson_data = json.loads(raw)

        return Lesson(
            topic_id=topic.id,
            title=lesson_data["title"],
            content=lesson_data["content"],
            difficulty=difficulty,
            objectives=lesson_data.get("objectives", []),
            examples=lesson_data.get("examples", []),
            exercises=lesson_data.get("exercises", []),
        )

    def generate_review_lesson(
        self,
        topic: Topic,
        subject: str,
        knowledge: TopicKnowledge,
        weak_areas: list[str] | None = None,
    ) -> Lesson:
        """Generate a review lesson focusing on areas where the student is weak.

        Args:
            topic: The topic to review.
            subject: The broader subject area.
            knowledge: Student's current knowledge state.
            weak_areas: Specific areas to focus on.

        Returns:
            A review-focused Lesson.
        """
        gaps = weak_areas or ["General review needed"]
        # For review, difficulty matches where the student currently is
        current_level = DifficultyLevel.from_numeric(
            max(0, DifficultyLevel.INTERMEDIATE.numeric - 1)
            if knowledge.score < 0.5
            else DifficultyLevel.INTERMEDIATE.numeric
        )

        return self.generate(
            topic=topic,
            subject=subject,
            difficulty=current_level,
            knowledge=knowledge,
            gap_descriptions=gaps,
            prerequisites_met=True,
        )

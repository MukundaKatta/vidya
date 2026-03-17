"""Detect and prioritize knowledge gaps from assessment results."""

from __future__ import annotations

from vidya.curriculum import Curriculum, Topic
from vidya.models import KnowledgeGap, MasteryLevel, TopicKnowledge
from vidya.student import KnowledgeState, Student


class GapDetector:
    """Identifies and prioritizes knowledge gaps for a student.

    Gaps are scored by severity and prioritized by considering:
      - Distance from target mastery
      - Whether the gap blocks progress on other topics (prerequisites)
      - Recency of assessment (stale assessments weigh more)
    """

    def __init__(self, target_score: float = 0.8) -> None:
        """Initialize the gap detector.

        Args:
            target_score: The minimum score to consider a topic "learned" (0.0-1.0).
        """
        if not 0.0 <= target_score <= 1.0:
            raise ValueError("target_score must be between 0.0 and 1.0")
        self.target_score = target_score

    def detect_gaps(
        self,
        student: Student,
        curriculum: Curriculum,
    ) -> list[KnowledgeGap]:
        """Find all knowledge gaps for a student in a curriculum.

        Args:
            student: The student to analyze.
            curriculum: The curriculum to check against.

        Returns:
            List of KnowledgeGap objects sorted by priority (highest first).
        """
        gaps: list[KnowledgeGap] = []
        topic_map = {t.id: t for t in curriculum.topics}
        dependents = self._build_dependents_map(curriculum)

        for topic in curriculum.topics:
            knowledge = student.knowledge.get(topic.id)

            if knowledge.score >= self.target_score:
                continue

            severity = self._compute_severity(knowledge, topic)
            blocking = self._find_blocked_topics(topic.id, dependents, topic_map)

            gap = KnowledgeGap(
                topic_id=topic.id,
                topic_name=topic.name,
                current_mastery=knowledge.mastery,
                current_score=knowledge.score,
                target_score=self.target_score,
                gap_severity=severity,
                blocking_topics=[t.name for t in blocking],
                recommended_action=self._recommend_action(knowledge, topic),
                priority=0,
            )
            gaps.append(gap)

        self._assign_priorities(gaps)
        return gaps

    def get_top_gaps(
        self,
        student: Student,
        curriculum: Curriculum,
        n: int = 5,
    ) -> list[KnowledgeGap]:
        """Get the top-N most critical knowledge gaps.

        Args:
            student: The student to analyze.
            curriculum: The curriculum to check against.
            n: Maximum number of gaps to return.

        Returns:
            List of top-N gaps sorted by priority.
        """
        gaps = self.detect_gaps(student, curriculum)
        return gaps[:n]

    def prerequisite_gaps(
        self,
        student: Student,
        curriculum: Curriculum,
        topic_id: str,
    ) -> list[KnowledgeGap]:
        """Find gaps specifically in the prerequisites of a target topic.

        Useful for determining what a student needs to learn before
        tackling a specific topic.

        Args:
            student: The student to analyze.
            curriculum: The curriculum context.
            topic_id: The target topic to check prerequisites for.

        Returns:
            List of prerequisite gaps sorted by priority.
        """
        prereqs = curriculum.get_prerequisites(topic_id)
        gaps: list[KnowledgeGap] = []

        for prereq in prereqs:
            knowledge = student.knowledge.get(prereq.id)
            if knowledge.score >= self.target_score:
                continue

            severity = self._compute_severity(knowledge, prereq)
            gap = KnowledgeGap(
                topic_id=prereq.id,
                topic_name=prereq.name,
                current_mastery=knowledge.mastery,
                current_score=knowledge.score,
                target_score=self.target_score,
                gap_severity=severity,
                blocking_topics=[curriculum.get_topic(topic_id).name]
                if curriculum.get_topic(topic_id)
                else [],
                recommended_action=self._recommend_action(knowledge, prereq),
                priority=0,
            )
            gaps.append(gap)

        self._assign_priorities(gaps)
        return gaps

    def _compute_severity(self, knowledge: TopicKnowledge, topic: Topic) -> float:
        """Compute gap severity from 0.0 (minor) to 1.0 (critical).

        Factors:
          - Distance from target score (primary)
          - Number of failed attempts (indicates persistent difficulty)
          - Topic difficulty (harder topics get slight severity boost)
        """
        score_gap = max(0.0, self.target_score - knowledge.score)
        base_severity = score_gap / self.target_score

        # Persistent difficulty bonus
        if knowledge.attempts > 0:
            failure_rate = 1.0 - knowledge.accuracy
            base_severity = 0.7 * base_severity + 0.2 * failure_rate
        else:
            # Never attempted: moderate severity since we have no data
            base_severity = max(base_severity, 0.5)

        # Topic difficulty adjustment (harder topics slightly more severe)
        difficulty_bonus = topic.difficulty.numeric * 0.025
        severity = min(1.0, base_severity + difficulty_bonus)

        return round(severity, 3)

    def _recommend_action(self, knowledge: TopicKnowledge, topic: Topic) -> str:
        """Generate a recommended action based on the knowledge state."""
        if knowledge.mastery == MasteryLevel.NOT_STARTED:
            return f"Begin learning '{topic.name}' with introductory material."
        if knowledge.mastery == MasteryLevel.NOVICE:
            if knowledge.attempts >= 3:
                return (
                    f"Review fundamentals of '{topic.name}'. "
                    "Consider simpler prerequisite material."
                )
            return f"Continue practicing '{topic.name}' with guided exercises."
        if knowledge.mastery == MasteryLevel.DEVELOPING:
            return (
                f"Practice '{topic.name}' with intermediate exercises. "
                "Focus on weak areas identified in assessments."
            )
        return f"Review '{topic.name}' to reinforce understanding."

    def _build_dependents_map(self, curriculum: Curriculum) -> dict[str, list[str]]:
        """Build a map of topic_id -> list of topic_ids that depend on it."""
        dependents: dict[str, list[str]] = {}
        for topic in curriculum.topics:
            for prereq_id in topic.prerequisites:
                dependents.setdefault(prereq_id, []).append(topic.id)
        return dependents

    def _find_blocked_topics(
        self,
        topic_id: str,
        dependents: dict[str, list[str]],
        topic_map: dict[str, Topic],
    ) -> list[Topic]:
        """Find all topics that are blocked by a gap in the given topic."""
        blocked_ids = dependents.get(topic_id, [])
        return [topic_map[tid] for tid in blocked_ids if tid in topic_map]

    def _assign_priorities(self, gaps: list[KnowledgeGap]) -> None:
        """Assign priority rankings to gaps (higher = more important).

        Considers severity and number of blocked topics.
        """
        for gap in gaps:
            blocking_weight = len(gap.blocking_topics) * 0.15
            gap.priority = round((gap.gap_severity + blocking_weight) * 100)

        gaps.sort(key=lambda g: g.priority, reverse=True)

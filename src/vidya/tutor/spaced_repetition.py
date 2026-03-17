"""SM-2 spaced repetition algorithm for long-term retention.

Implements the SuperMemo SM-2 algorithm:
  - Quality grades 0-5 (0-2 = failure, 3-5 = success)
  - Easiness factor adjusted per review
  - Interval grows exponentially on consecutive successes
  - Resets to initial interval on failure
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from vidya.models import SpacedRepetitionCard, TopicKnowledge


# SM-2 quality grade thresholds
MIN_EASINESS_FACTOR = 1.3
DEFAULT_EASINESS_FACTOR = 2.5


def quality_from_score(score: float) -> int:
    """Convert a 0.0-1.0 score to an SM-2 quality grade (0-5).

    Mapping:
        0.0-0.19 -> 0  (complete blackout)
        0.20-0.39 -> 1  (incorrect, but recognized on reveal)
        0.40-0.59 -> 2  (incorrect, but easy to recall on reveal)
        0.60-0.74 -> 3  (correct with serious difficulty)
        0.75-0.89 -> 4  (correct with hesitation)
        0.90-1.0  -> 5  (perfect response)
    """
    if score < 0.20:
        return 0
    if score < 0.40:
        return 1
    if score < 0.60:
        return 2
    if score < 0.75:
        return 3
    if score < 0.90:
        return 4
    return 5


def compute_sm2(
    quality: int,
    repetition_number: int,
    easiness_factor: float,
    interval_days: int,
) -> tuple[int, float, int]:
    """Run one iteration of the SM-2 algorithm.

    Args:
        quality: Response quality grade (0-5).
        repetition_number: Current repetition count.
        easiness_factor: Current easiness factor (>= 1.3).
        interval_days: Current interval in days.

    Returns:
        Tuple of (new_repetition_number, new_easiness_factor, new_interval_days).
    """
    if quality < 0 or quality > 5:
        raise ValueError(f"Quality must be 0-5, got {quality}")

    # Update easiness factor
    new_ef = easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(MIN_EASINESS_FACTOR, new_ef)

    if quality < 3:
        # Failure: reset repetitions, start from the beginning
        new_rep = 0
        new_interval = 1
    else:
        # Success: advance repetition count
        new_rep = repetition_number + 1
        if new_rep == 1:
            new_interval = 1
        elif new_rep == 2:
            new_interval = 6
        else:
            new_interval = round(interval_days * new_ef)

    return new_rep, new_ef, new_interval


class SpacedRepetitionScheduler:
    """Manages spaced repetition scheduling for student review cards."""

    def __init__(self) -> None:
        self._cards: dict[str, list[SpacedRepetitionCard]] = {}  # student_id -> cards

    def add_card(self, card: SpacedRepetitionCard) -> None:
        """Register a new review card."""
        if card.student_id not in self._cards:
            self._cards[card.student_id] = []
        self._cards[card.student_id].append(card)

    def create_card(
        self,
        student_id: str,
        topic_id: str,
        question: str,
        answer: str,
    ) -> SpacedRepetitionCard:
        """Create and register a new review card."""
        card = SpacedRepetitionCard(
            student_id=student_id,
            topic_id=topic_id,
            question=question,
            answer=answer,
        )
        self.add_card(card)
        return card

    def review_card(
        self,
        card: SpacedRepetitionCard,
        score: float,
        review_time: datetime | None = None,
    ) -> SpacedRepetitionCard:
        """Process a review of a card and update its schedule.

        Args:
            card: The card being reviewed.
            score: Performance score from 0.0 to 1.0.
            review_time: When the review occurred (defaults to now).

        Returns:
            The updated card with new scheduling parameters.
        """
        now = review_time or datetime.utcnow()
        quality = quality_from_score(score)

        new_rep, new_ef, new_interval = compute_sm2(
            quality=quality,
            repetition_number=card.repetition_number,
            easiness_factor=card.easiness_factor,
            interval_days=card.interval_days,
        )

        card.repetition_number = new_rep
        card.easiness_factor = new_ef
        card.interval_days = new_interval
        card.next_review = now + timedelta(days=new_interval)
        card.last_reviewed = now
        card.total_reviews += 1

        return card

    def update_topic_knowledge(
        self, knowledge: TopicKnowledge, score: float, review_time: datetime | None = None
    ) -> TopicKnowledge:
        """Update a TopicKnowledge entry using SM-2 after a review.

        Args:
            knowledge: The topic knowledge state to update.
            score: Performance score from 0.0 to 1.0.
            review_time: When the review occurred.

        Returns:
            The updated TopicKnowledge.
        """
        now = review_time or datetime.utcnow()
        quality = quality_from_score(score)

        new_rep, new_ef, new_interval = compute_sm2(
            quality=quality,
            repetition_number=knowledge.repetition_number,
            easiness_factor=knowledge.easiness_factor,
            interval_days=knowledge.interval_days,
        )

        knowledge.repetition_number = new_rep
        knowledge.easiness_factor = new_ef
        knowledge.interval_days = new_interval
        knowledge.next_review = now + timedelta(days=new_interval)
        knowledge.last_practiced = now

        return knowledge

    def get_due_cards(
        self, student_id: str, as_of: datetime | None = None
    ) -> list[SpacedRepetitionCard]:
        """Get all cards due for review for a student.

        Args:
            student_id: The student's ID.
            as_of: Reference time (defaults to now).

        Returns:
            List of cards due for review, sorted by due date (most overdue first).
        """
        now = as_of or datetime.utcnow()
        cards = self._cards.get(student_id, [])
        due = [c for c in cards if c.next_review <= now]
        due.sort(key=lambda c: c.next_review)
        return due

    def get_all_cards(self, student_id: str) -> list[SpacedRepetitionCard]:
        """Get all cards for a student."""
        return list(self._cards.get(student_id, []))

    def stats(self, student_id: str) -> dict[str, int]:
        """Get review statistics for a student."""
        cards = self._cards.get(student_id, [])
        now = datetime.utcnow()
        return {
            "total_cards": len(cards),
            "due_now": sum(1 for c in cards if c.next_review <= now),
            "total_reviews": sum(c.total_reviews for c in cards),
            "mature_cards": sum(1 for c in cards if c.interval_days >= 21),
            "young_cards": sum(1 for c in cards if 0 < c.interval_days < 21),
            "new_cards": sum(1 for c in cards if c.total_reviews == 0),
        }

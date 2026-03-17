"""Tests for the SM-2 spaced repetition algorithm."""

from datetime import datetime, timedelta

import pytest

from vidya.models import SpacedRepetitionCard, TopicKnowledge
from vidya.tutor.spaced_repetition import (
    MIN_EASINESS_FACTOR,
    SpacedRepetitionScheduler,
    compute_sm2,
    quality_from_score,
)


class TestQualityFromScore:
    """Tests for score-to-quality conversion."""

    def test_perfect_score(self) -> None:
        assert quality_from_score(1.0) == 5

    def test_high_score(self) -> None:
        assert quality_from_score(0.85) == 4

    def test_passing_score(self) -> None:
        assert quality_from_score(0.70) == 3

    def test_near_fail(self) -> None:
        assert quality_from_score(0.55) == 2

    def test_low_score(self) -> None:
        assert quality_from_score(0.30) == 1

    def test_zero_score(self) -> None:
        assert quality_from_score(0.0) == 0

    def test_boundary_090(self) -> None:
        assert quality_from_score(0.90) == 5

    def test_boundary_075(self) -> None:
        assert quality_from_score(0.75) == 4

    def test_boundary_060(self) -> None:
        assert quality_from_score(0.60) == 3


class TestComputeSM2:
    """Tests for the core SM-2 algorithm."""

    def test_first_success_gives_1_day_interval(self) -> None:
        rep, ef, interval = compute_sm2(quality=4, repetition_number=0, easiness_factor=2.5, interval_days=0)
        assert rep == 1
        assert interval == 1

    def test_second_success_gives_6_day_interval(self) -> None:
        rep, ef, interval = compute_sm2(quality=4, repetition_number=1, easiness_factor=2.5, interval_days=1)
        assert rep == 2
        assert interval == 6

    def test_third_success_multiplies_by_ef(self) -> None:
        rep, ef, interval = compute_sm2(quality=4, repetition_number=2, easiness_factor=2.5, interval_days=6)
        assert rep == 3
        assert interval == round(6 * ef)

    def test_failure_resets_repetition(self) -> None:
        rep, ef, interval = compute_sm2(quality=1, repetition_number=5, easiness_factor=2.5, interval_days=30)
        assert rep == 0
        assert interval == 1

    def test_perfect_quality_increases_ef(self) -> None:
        _, ef, _ = compute_sm2(quality=5, repetition_number=0, easiness_factor=2.5, interval_days=0)
        assert ef > 2.5

    def test_low_quality_decreases_ef(self) -> None:
        _, ef, _ = compute_sm2(quality=3, repetition_number=0, easiness_factor=2.5, interval_days=0)
        assert ef < 2.5

    def test_ef_never_below_minimum(self) -> None:
        _, ef, _ = compute_sm2(quality=0, repetition_number=0, easiness_factor=1.3, interval_days=0)
        assert ef >= MIN_EASINESS_FACTOR

    def test_invalid_quality_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_sm2(quality=6, repetition_number=0, easiness_factor=2.5, interval_days=0)
        with pytest.raises(ValueError):
            compute_sm2(quality=-1, repetition_number=0, easiness_factor=2.5, interval_days=0)

    def test_intervals_grow_with_consecutive_successes(self) -> None:
        """Verify that intervals increase over consecutive successful reviews."""
        rep, ef, interval = 0, 2.5, 0
        intervals = []
        for _ in range(6):
            rep, ef, interval = compute_sm2(quality=4, repetition_number=rep, easiness_factor=ef, interval_days=interval)
            intervals.append(interval)
        # Intervals should be non-decreasing after the first two
        assert intervals[0] == 1
        assert intervals[1] == 6
        for i in range(2, len(intervals)):
            assert intervals[i] >= intervals[i - 1]


class TestSpacedRepetitionScheduler:
    """Tests for the scheduler that manages cards."""

    def setup_method(self) -> None:
        self.scheduler = SpacedRepetitionScheduler()
        self.student_id = "student_001"

    def test_create_card(self) -> None:
        card = self.scheduler.create_card(
            student_id=self.student_id,
            topic_id="topic_1",
            question="What is Python?",
            answer="A programming language.",
        )
        assert card.student_id == self.student_id
        assert card.easiness_factor == 2.5
        assert card.interval_days == 0
        assert card.repetition_number == 0

    def test_review_card_perfect(self) -> None:
        card = self.scheduler.create_card(
            student_id=self.student_id,
            topic_id="topic_1",
            question="Q",
            answer="A",
        )
        updated = self.scheduler.review_card(card, score=0.95)
        assert updated.repetition_number == 1
        assert updated.interval_days == 1
        assert updated.total_reviews == 1
        assert updated.last_reviewed is not None

    def test_review_card_failure_resets(self) -> None:
        card = self.scheduler.create_card(
            student_id=self.student_id,
            topic_id="topic_1",
            question="Q",
            answer="A",
        )
        # First succeed a few times
        self.scheduler.review_card(card, score=0.95)
        self.scheduler.review_card(card, score=0.90)
        assert card.repetition_number == 2
        # Then fail
        self.scheduler.review_card(card, score=0.1)
        assert card.repetition_number == 0
        assert card.interval_days == 1

    def test_get_due_cards(self) -> None:
        now = datetime.utcnow()
        # Card due in the past
        card1 = self.scheduler.create_card(self.student_id, "t1", "Q1", "A1")
        card1.next_review = now - timedelta(hours=1)
        # Card due in the future
        card2 = self.scheduler.create_card(self.student_id, "t2", "Q2", "A2")
        card2.next_review = now + timedelta(days=5)

        due = self.scheduler.get_due_cards(self.student_id, as_of=now)
        assert len(due) == 1
        assert due[0].topic_id == "t1"

    def test_stats(self) -> None:
        now = datetime.utcnow()
        card = self.scheduler.create_card(self.student_id, "t1", "Q", "A")
        card.next_review = now - timedelta(hours=1)
        stats = self.scheduler.stats(self.student_id)
        assert stats["total_cards"] == 1
        assert stats["due_now"] == 1
        assert stats["new_cards"] == 1

    def test_update_topic_knowledge(self) -> None:
        knowledge = TopicKnowledge(topic_id="t1")
        updated = self.scheduler.update_topic_knowledge(knowledge, score=0.85)
        assert updated.repetition_number == 1
        assert updated.interval_days == 1
        assert updated.next_review is not None
        assert updated.last_practiced is not None

    def test_multiple_students_isolated(self) -> None:
        self.scheduler.create_card("s1", "t1", "Q1", "A1")
        self.scheduler.create_card("s2", "t2", "Q2", "A2")
        assert len(self.scheduler.get_all_cards("s1")) == 1
        assert len(self.scheduler.get_all_cards("s2")) == 1
        assert len(self.scheduler.get_all_cards("s3")) == 0

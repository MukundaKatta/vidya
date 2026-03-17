"""Tests for tutor components: gap detection, difficulty adaptation, curriculum, and student."""

from datetime import datetime, timedelta

import pytest

from vidya.curriculum import Curriculum, Lesson, Topic
from vidya.models import DifficultyLevel, KnowledgeGap, MasteryLevel, TopicKnowledge
from vidya.student import KnowledgeState, LearningSession, Student
from vidya.tutor.difficulty_adapter import DifficultyAdapter, PerformanceWindow
from vidya.tutor.gap_detector import GapDetector


# ---------------------------------------------------------------------------
# Curriculum tests
# ---------------------------------------------------------------------------


class TestCurriculum:
    def test_add_and_get_topic(self) -> None:
        c = Curriculum(name="Test", subject="Math")
        t = Topic(name="Algebra", description="Basic algebra")
        c.add_topic(t)
        assert c.get_topic(t.id) is t
        assert c.get_topic_by_name("algebra") is t

    def test_get_topic_by_name_case_insensitive(self) -> None:
        c = Curriculum(name="Test", subject="Math")
        t = Topic(name="Calculus")
        c.add_topic(t)
        assert c.get_topic_by_name("CALCULUS") is t

    def test_get_topic_not_found(self) -> None:
        c = Curriculum(name="Test", subject="Math")
        assert c.get_topic("nonexistent") is None
        assert c.get_topic_by_name("nonexistent") is None

    def test_topological_order_no_deps(self) -> None:
        c = Curriculum(name="Test", subject="Math")
        t1 = Topic(name="A")
        t2 = Topic(name="B")
        c.add_topic(t1)
        c.add_topic(t2)
        order = c.topological_order()
        assert len(order) == 2

    def test_topological_order_with_deps(self) -> None:
        c = Curriculum(name="Test", subject="Math")
        t1 = Topic(name="Basics")
        t2 = Topic(name="Advanced", prerequisites=[t1.id])
        c.add_topic(t1)
        c.add_topic(t2)
        order = c.topological_order()
        assert order.index(t1) < order.index(t2)

    def test_prerequisites(self) -> None:
        c = Curriculum(name="Test", subject="Math")
        t1 = Topic(name="Prereq")
        t2 = Topic(name="Dependent", prerequisites=[t1.id])
        c.add_topic(t1)
        c.add_topic(t2)
        prereqs = c.get_prerequisites(t2.id)
        assert len(prereqs) == 1
        assert prereqs[0] is t1


class TestLesson:
    def test_lesson_creation(self) -> None:
        lesson = Lesson(
            topic_id="t1",
            title="Intro to Algebra",
            content="This is a lesson.",
            difficulty=DifficultyLevel.BEGINNER,
            objectives=["Learn basics"],
            examples=["2 + x = 5"],
        )
        assert lesson.title == "Intro to Algebra"
        assert lesson.difficulty == DifficultyLevel.BEGINNER
        assert len(lesson.objectives) == 1


# ---------------------------------------------------------------------------
# Student and KnowledgeState tests
# ---------------------------------------------------------------------------


class TestKnowledgeState:
    def test_get_creates_default(self) -> None:
        ks = KnowledgeState()
        tk = ks.get("topic_1")
        assert tk.topic_id == "topic_1"
        assert tk.mastery == MasteryLevel.NOT_STARTED
        assert tk.score == 0.0

    def test_update_from_result_correct(self) -> None:
        ks = KnowledgeState()
        tk = ks.update_from_result("topic_1", is_correct=True, score=0.9)
        assert tk.attempts == 1
        assert tk.correct_count == 1
        assert tk.score > 0.0

    def test_update_from_result_incorrect(self) -> None:
        ks = KnowledgeState()
        tk = ks.update_from_result("topic_1", is_correct=False, score=0.2)
        assert tk.attempts == 1
        assert tk.correct_count == 0

    def test_weakest_topics(self) -> None:
        ks = KnowledgeState()
        ks.update_from_result("t1", True, 0.9)
        ks.update_from_result("t2", False, 0.2)
        ks.update_from_result("t3", True, 0.5)
        weakest = ks.weakest_topics(n=2)
        assert len(weakest) == 2
        assert weakest[0].topic_id == "t2"

    def test_topics_due_for_review(self) -> None:
        ks = KnowledgeState()
        tk = ks.get("t1")
        tk.next_review = datetime.utcnow() - timedelta(hours=1)
        due = ks.topics_due_for_review()
        assert "t1" in due


class TestStudent:
    def test_student_creation(self) -> None:
        s = Student(name="Alice")
        assert s.name == "Alice"
        assert s.current_difficulty == DifficultyLevel.BEGINNER

    def test_start_session(self) -> None:
        s = Student(name="Alice")
        session = s.start_session("t1")
        assert session.model.student_id == s.id
        assert session.model.topic_id == "t1"
        assert s.model.total_sessions == 1

    def test_session_accuracy(self) -> None:
        s = Student(name="Alice")
        session = s.start_session("t1")
        session.record_answer(True)
        session.record_answer(True)
        session.record_answer(False)
        assert session.accuracy == pytest.approx(2 / 3)


class TestLearningSession:
    def test_end_session(self) -> None:
        session = LearningSession("s1", "t1", DifficultyLevel.BEGINNER)
        session.record_answer(True)
        model = session.end()
        assert model.ended_at is not None
        assert model.duration is not None


# ---------------------------------------------------------------------------
# DifficultyAdapter tests
# ---------------------------------------------------------------------------


class TestPerformanceWindow:
    def test_mean(self) -> None:
        w = PerformanceWindow(max_size=5)
        w.add(0.8)
        w.add(0.6)
        assert w.mean == pytest.approx(0.7)

    def test_max_size(self) -> None:
        w = PerformanceWindow(max_size=3)
        for v in [0.1, 0.2, 0.3, 0.4, 0.5]:
            w.add(v)
        assert w.count == 3
        assert w.scores == [0.3, 0.4, 0.5]

    def test_trend_positive(self) -> None:
        w = PerformanceWindow(max_size=6)
        for v in [0.3, 0.4, 0.5, 0.7, 0.8, 0.9]:
            w.add(v)
        assert w.trend > 0

    def test_trend_negative(self) -> None:
        w = PerformanceWindow(max_size=6)
        for v in [0.9, 0.8, 0.7, 0.3, 0.2, 0.1]:
            w.add(v)
        assert w.trend < 0


class TestDifficultyAdapter:
    def test_no_change_below_min_observations(self) -> None:
        adapter = DifficultyAdapter(min_observations=5)
        adapter.record_performance(1.0)
        adapter.record_performance(1.0)
        assert adapter.current_difficulty == DifficultyLevel.BEGINNER

    def test_increases_on_high_performance(self) -> None:
        adapter = DifficultyAdapter(
            initial_difficulty=DifficultyLevel.BEGINNER,
            min_observations=3,
            upper_threshold=0.85,
        )
        for _ in range(5):
            adapter.record_performance(0.95)
        assert adapter.current_difficulty.numeric > DifficultyLevel.BEGINNER.numeric

    def test_decreases_on_low_performance(self) -> None:
        adapter = DifficultyAdapter(
            initial_difficulty=DifficultyLevel.INTERMEDIATE,
            min_observations=3,
            lower_threshold=0.45,
        )
        for _ in range(5):
            adapter.record_performance(0.2)
        assert adapter.current_difficulty.numeric < DifficultyLevel.INTERMEDIATE.numeric

    def test_stays_at_minimum(self) -> None:
        adapter = DifficultyAdapter(
            initial_difficulty=DifficultyLevel.BEGINNER,
            min_observations=3,
        )
        for _ in range(5):
            adapter.record_performance(0.1)
        assert adapter.current_difficulty == DifficultyLevel.BEGINNER

    def test_stays_at_maximum(self) -> None:
        adapter = DifficultyAdapter(
            initial_difficulty=DifficultyLevel.EXPERT,
            min_observations=3,
        )
        for _ in range(5):
            adapter.record_performance(0.99)
        assert adapter.current_difficulty == DifficultyLevel.EXPERT

    def test_suggest_does_not_mutate(self) -> None:
        adapter = DifficultyAdapter(
            initial_difficulty=DifficultyLevel.BEGINNER,
            min_observations=3,
        )
        for _ in range(5):
            adapter.record_performance(0.95)
        before = adapter.current_difficulty
        _ = adapter.suggest_difficulty()
        assert adapter.current_difficulty == before

    def test_reset(self) -> None:
        adapter = DifficultyAdapter()
        adapter.record_performance(0.5)
        adapter.reset(DifficultyLevel.EXPERT)
        assert adapter.current_difficulty == DifficultyLevel.EXPERT
        assert adapter.window.count == 0


# ---------------------------------------------------------------------------
# GapDetector tests
# ---------------------------------------------------------------------------


class TestGapDetector:
    def _make_curriculum(self) -> tuple[Curriculum, Topic, Topic, Topic]:
        c = Curriculum(name="Test", subject="Math")
        t1 = Topic(name="Addition", difficulty=DifficultyLevel.BEGINNER)
        t2 = Topic(name="Multiplication", prerequisites=[t1.id], difficulty=DifficultyLevel.ELEMENTARY)
        t3 = Topic(name="Algebra", prerequisites=[t2.id], difficulty=DifficultyLevel.INTERMEDIATE)
        c.add_topic(t1)
        c.add_topic(t2)
        c.add_topic(t3)
        return c, t1, t2, t3

    def test_detect_all_gaps_for_new_student(self) -> None:
        c, t1, t2, t3 = self._make_curriculum()
        student = Student(name="Alice")
        detector = GapDetector(target_score=0.8)
        gaps = detector.detect_gaps(student, c)
        assert len(gaps) == 3  # All topics are gaps for a new student

    def test_no_gaps_when_all_mastered(self) -> None:
        c, t1, t2, t3 = self._make_curriculum()
        student = Student(name="Alice")
        for topic in [t1, t2, t3]:
            tk = student.knowledge.get(topic.id)
            tk.score = 0.95
            tk.mastery = MasteryLevel.MASTERED
            tk.attempts = 10
            tk.correct_count = 9
        detector = GapDetector(target_score=0.8)
        gaps = detector.detect_gaps(student, c)
        assert len(gaps) == 0

    def test_gaps_sorted_by_priority(self) -> None:
        c, t1, t2, t3 = self._make_curriculum()
        student = Student(name="Alice")
        # t1 is well-known, t2 is weak, t3 is unknown
        tk1 = student.knowledge.get(t1.id)
        tk1.score = 0.9
        tk1.mastery = MasteryLevel.MASTERED
        tk1.attempts = 5
        tk1.correct_count = 5

        tk2 = student.knowledge.get(t2.id)
        tk2.score = 0.3
        tk2.mastery = MasteryLevel.NOVICE
        tk2.attempts = 5
        tk2.correct_count = 2

        detector = GapDetector(target_score=0.8)
        gaps = detector.detect_gaps(student, c)
        # t2 and t3 should be gaps, t1 should not
        topic_ids = [g.topic_id for g in gaps]
        assert t1.id not in topic_ids
        assert t2.id in topic_ids
        assert t3.id in topic_ids

    def test_blocking_topics_detected(self) -> None:
        c, t1, t2, t3 = self._make_curriculum()
        student = Student(name="Alice")
        detector = GapDetector(target_score=0.8)
        gaps = detector.detect_gaps(student, c)
        gap_map = {g.topic_id: g for g in gaps}
        # t1 blocks t2
        assert len(gap_map[t1.id].blocking_topics) > 0

    def test_prerequisite_gaps(self) -> None:
        c, t1, t2, t3 = self._make_curriculum()
        student = Student(name="Alice")
        detector = GapDetector(target_score=0.8)
        prereq_gaps = detector.prerequisite_gaps(student, c, t3.id)
        # t3 depends on t2
        assert any(g.topic_id == t2.id for g in prereq_gaps)

    def test_get_top_gaps(self) -> None:
        c, t1, t2, t3 = self._make_curriculum()
        student = Student(name="Alice")
        detector = GapDetector(target_score=0.8)
        top = detector.get_top_gaps(student, c, n=2)
        assert len(top) <= 2

    def test_target_score_validation(self) -> None:
        with pytest.raises(ValueError):
            GapDetector(target_score=1.5)
        with pytest.raises(ValueError):
            GapDetector(target_score=-0.1)


# ---------------------------------------------------------------------------
# DifficultyLevel model tests
# ---------------------------------------------------------------------------


class TestDifficultyLevel:
    def test_numeric_roundtrip(self) -> None:
        for level in DifficultyLevel:
            assert DifficultyLevel.from_numeric(level.numeric) == level

    def test_from_numeric_clamps_high(self) -> None:
        result = DifficultyLevel.from_numeric(100)
        assert result == DifficultyLevel.EXPERT

    def test_from_numeric_clamps_low(self) -> None:
        result = DifficultyLevel.from_numeric(-5)
        assert result == DifficultyLevel.BEGINNER

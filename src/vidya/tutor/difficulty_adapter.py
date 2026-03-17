"""Adjust difficulty in real-time based on student performance."""

from __future__ import annotations

from dataclasses import dataclass, field

from vidya.models import DifficultyLevel


@dataclass
class PerformanceWindow:
    """Sliding window of recent performance scores."""

    max_size: int = 10
    scores: list[float] = field(default_factory=list)

    def add(self, score: float) -> None:
        """Add a score to the window."""
        self.scores.append(max(0.0, min(1.0, score)))
        if len(self.scores) > self.max_size:
            self.scores.pop(0)

    @property
    def mean(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores) / len(self.scores)

    @property
    def trend(self) -> float:
        """Compute recent trend (-1.0 to 1.0). Positive means improving."""
        if len(self.scores) < 3:
            return 0.0
        half = len(self.scores) // 2
        first_half = sum(self.scores[:half]) / half
        second_half = sum(self.scores[half:]) / (len(self.scores) - half)
        return second_half - first_half

    @property
    def count(self) -> int:
        return len(self.scores)

    def clear(self) -> None:
        self.scores.clear()


class DifficultyAdapter:
    """Adapts difficulty level in real-time based on rolling performance.

    The adapter uses a sliding window of recent scores to decide when
    to increase or decrease difficulty. It avoids rapid oscillation by
    requiring a minimum number of observations and a sustained trend.

    Thresholds:
      - Increase difficulty when mean score > upper_threshold (default 0.85)
        and trend is positive.
      - Decrease difficulty when mean score < lower_threshold (default 0.45)
        or trend is strongly negative.
    """

    def __init__(
        self,
        initial_difficulty: DifficultyLevel = DifficultyLevel.BEGINNER,
        window_size: int = 10,
        upper_threshold: float = 0.85,
        lower_threshold: float = 0.45,
        min_observations: int = 3,
    ) -> None:
        self.current_difficulty = initial_difficulty
        self.upper_threshold = upper_threshold
        self.lower_threshold = lower_threshold
        self.min_observations = min_observations
        self._window = PerformanceWindow(max_size=window_size)
        self._history: list[tuple[DifficultyLevel, float]] = []

    @property
    def window(self) -> PerformanceWindow:
        return self._window

    @property
    def adjustment_history(self) -> list[tuple[DifficultyLevel, float]]:
        """History of (difficulty_level, mean_score_at_change) tuples."""
        return list(self._history)

    def record_performance(self, score: float) -> DifficultyLevel:
        """Record a performance score and possibly adjust difficulty.

        Args:
            score: Performance score from 0.0 to 1.0.

        Returns:
            The current difficulty level (may have changed).
        """
        self._window.add(score)

        if self._window.count < self.min_observations:
            return self.current_difficulty

        mean = self._window.mean
        trend = self._window.trend

        new_difficulty = self.current_difficulty

        if mean >= self.upper_threshold and trend >= -0.05:
            new_difficulty = DifficultyLevel.from_numeric(
                self.current_difficulty.numeric + 1
            )
        elif mean <= self.lower_threshold or trend < -0.25:
            new_difficulty = DifficultyLevel.from_numeric(
                self.current_difficulty.numeric - 1
            )

        if new_difficulty != self.current_difficulty:
            self._history.append((new_difficulty, mean))
            self.current_difficulty = new_difficulty
            self._window.clear()

        return self.current_difficulty

    def suggest_difficulty(self) -> DifficultyLevel:
        """Suggest the appropriate difficulty without committing to a change.

        Useful for previewing what would happen without modifying state.
        """
        if self._window.count < self.min_observations:
            return self.current_difficulty

        mean = self._window.mean
        trend = self._window.trend

        if mean >= self.upper_threshold and trend >= -0.05:
            return DifficultyLevel.from_numeric(self.current_difficulty.numeric + 1)
        if mean <= self.lower_threshold or trend < -0.25:
            return DifficultyLevel.from_numeric(self.current_difficulty.numeric - 1)

        return self.current_difficulty

    def reset(self, difficulty: DifficultyLevel | None = None) -> None:
        """Reset the adapter state.

        Args:
            difficulty: New starting difficulty (keeps current if None).
        """
        if difficulty is not None:
            self.current_difficulty = difficulty
        self._window.clear()
        self._history.clear()

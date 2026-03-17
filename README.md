# Vidya - AI Adaptive Tutoring Platform

Vidya is an intelligent tutoring system that personalizes learning through AI-driven lesson generation, knowledge gap detection, difficulty adaptation, and spaced repetition scheduling.

## Features

- **Personalized Lesson Generation** - AI-generated lessons tailored to student knowledge state
- **Knowledge Assessment** - Evaluate student understanding per topic
- **Gap Detection** - Identify and prioritize knowledge gaps
- **Difficulty Adaptation** - Real-time difficulty adjustment based on performance
- **Spaced Repetition** - SM-2 algorithm for optimal long-term retention

## Installation

```bash
pip install -e .
```

## Usage

### CLI Commands

```bash
# Start a teaching session
vidya teach --subject "Python Programming" --topic "List Comprehensions"

# Assess knowledge on a topic
vidya assess --subject "Mathematics" --topic "Linear Algebra"

# Practice with spaced repetition
vidya practice --student "student_001"
```

### Python API

```python
from vidya.curriculum import Curriculum, Topic
from vidya.student import Student
from vidya.tutor.lesson_generator import LessonGenerator
from vidya.tutor.knowledge_assessor import KnowledgeAssessor
from vidya.tutor.gap_detector import GapDetector

# See examples/run_tutoring_session.py for a full example
```

## Architecture

- `vidya.curriculum` - Curriculum, Topic, and Lesson data models
- `vidya.student` - Student profile and knowledge state tracking
- `vidya.tutor.lesson_generator` - AI-powered personalized lesson creation
- `vidya.tutor.knowledge_assessor` - Student knowledge evaluation
- `vidya.tutor.gap_detector` - Knowledge gap identification and prioritization
- `vidya.tutor.difficulty_adapter` - Real-time difficulty adjustment
- `vidya.tutor.spaced_repetition` - SM-2 spaced repetition scheduling

## License

MIT

"""Assess student knowledge state per topic using AI-generated questions."""

from __future__ import annotations

import json
from typing import Optional

import anthropic

from vidya.curriculum import Curriculum, Topic
from vidya.models import (
    AssessmentQuestion,
    AssessmentResult,
    DifficultyLevel,
    MasteryLevel,
    QuestionType,
)
from vidya.student import KnowledgeState, Student


_GENERATE_QUESTIONS_PROMPT = """\
You are an expert educational assessor. Generate {count} assessment questions for the topic below.

Subject: {subject}
Topic: {topic_name}
Description: {topic_description}
Difficulty: {difficulty}
Question types to include: {question_types}

Return a JSON array of question objects, each with:
- "question": the question text
- "question_type": one of {question_types}
- "options": array of options (for multiple_choice, otherwise empty array)
- "correct_answer": the correct answer
- "explanation": brief explanation of the answer
- "difficulty": "{difficulty}"

Return ONLY the JSON array, no other text.
"""

_EVALUATE_ANSWER_PROMPT = """\
You are an expert educational assessor. Evaluate the student's answer.

Topic: {topic_name}
Question: {question}
Correct answer: {correct_answer}
Student's answer: {student_answer}

Evaluate the student's answer and return a JSON object with:
- "is_correct": boolean (true if the answer demonstrates understanding, even if not word-for-word)
- "score": float from 0.0 to 1.0 (partial credit allowed)
- "feedback": constructive feedback for the student

Return ONLY the JSON object, no other text.
"""


class KnowledgeAssessor:
    """Assesses student knowledge using AI-generated questions and evaluation."""

    def __init__(self, client: anthropic.Anthropic | None = None, model: str = "claude-sonnet-4-20250514") -> None:
        self._client = client or anthropic.Anthropic()
        self._model = model

    def generate_questions(
        self,
        topic: Topic,
        subject: str,
        count: int = 5,
        difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
        question_types: list[QuestionType] | None = None,
    ) -> list[AssessmentQuestion]:
        """Generate assessment questions for a topic using AI.

        Args:
            topic: The topic to assess.
            subject: The broader subject area.
            count: Number of questions to generate.
            difficulty: Target difficulty level.
            question_types: Types of questions to include.

        Returns:
            List of generated assessment questions.
        """
        qtypes = question_types or [QuestionType.SHORT_ANSWER, QuestionType.MULTIPLE_CHOICE]
        type_names = ", ".join(qt.value for qt in qtypes)

        prompt = _GENERATE_QUESTIONS_PROMPT.format(
            count=count,
            subject=subject,
            topic_name=topic.name,
            topic_description=topic.description,
            difficulty=difficulty.value,
            question_types=type_names,
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]

        questions_data = json.loads(raw)
        questions: list[AssessmentQuestion] = []
        for qd in questions_data:
            q = AssessmentQuestion(
                topic_id=topic.id,
                question=qd["question"],
                question_type=QuestionType(qd.get("question_type", "short_answer")),
                options=qd.get("options", []),
                correct_answer=qd.get("correct_answer", ""),
                difficulty=difficulty,
                explanation=qd.get("explanation", ""),
            )
            questions.append(q)

        return questions

    def evaluate_answer(
        self,
        topic_name: str,
        question: AssessmentQuestion,
        student_answer: str,
    ) -> AssessmentResult:
        """Evaluate a student's answer to a question using AI.

        Args:
            topic_name: Name of the topic being assessed.
            question: The assessment question.
            student_answer: The student's answer text.

        Returns:
            Assessment result with score and feedback.
        """
        prompt = _EVALUATE_ANSWER_PROMPT.format(
            topic_name=topic_name,
            question=question.question,
            correct_answer=question.correct_answer,
            student_answer=student_answer,
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]

        result_data = json.loads(raw)

        return AssessmentResult(
            question_id=question.id,
            topic_id=question.topic_id,
            student_answer=student_answer,
            is_correct=result_data["is_correct"],
            score=float(result_data["score"]),
            feedback=result_data.get("feedback", ""),
        )

    def assess_topic(
        self,
        student: Student,
        topic: Topic,
        subject: str,
        answers: dict[str, str],
        count: int = 5,
    ) -> list[AssessmentResult]:
        """Run a full topic assessment: generate questions, evaluate provided answers.

        This is a convenience method for batch assessment when answers
        are already collected (e.g., from a CLI session).

        Args:
            student: The student being assessed.
            topic: The topic to assess.
            subject: The broader subject area.
            answers: Mapping of question_id -> student answer.
            count: Number of questions to generate.

        Returns:
            List of assessment results.
        """
        questions = self.generate_questions(topic, subject, count=count)
        results: list[AssessmentResult] = []

        for q in questions:
            answer_text = answers.get(q.id, "")
            if not answer_text:
                continue
            result = self.evaluate_answer(topic.name, q, answer_text)
            student.knowledge.update_from_result(
                topic_id=topic.id,
                is_correct=result.is_correct,
                score=result.score,
            )
            results.append(result)

        return results

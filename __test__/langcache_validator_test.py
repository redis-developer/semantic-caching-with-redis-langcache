import pytest
from pydantic import ValidationError

from app.components.langcache.validator import AskQuestionBody


def test_ask_question_body_accepts_a_non_empty_question():
    result = AskQuestionBody.model_validate({"question": "How do I reset my password?"})

    assert result.question == "How do I reset my password?"


def test_ask_question_body_rejects_empty_question():
    with pytest.raises(ValidationError, match="Question must not be empty"):
        AskQuestionBody.model_validate({"question": ""})

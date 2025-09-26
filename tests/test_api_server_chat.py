"""Tests for chat history handling in the API server."""

from packages.legal_tools.api_server import _partition_history_and_question


def test_partition_history_and_question_extracts_latest_user():
    messages = [
        {"role": "system", "content": "지침"},
        {"role": "user", "content": "첫 질문"},
        {"role": "assistant", "content": "응답"},
        {"role": "user", "content": "후속 질문"},
    ]

    history, question = _partition_history_and_question(messages)

    assert question == "후속 질문"
    assert history == [
        {"role": "system", "content": "지침"},
        {"role": "user", "content": "첫 질문"},
        {"role": "assistant", "content": "응답"},
    ]


def test_partition_history_ignores_unknown_roles_and_empty_content():
    messages = [
        {"role": "user", "content": "A"},
        {"role": "assistant", "content": ""},
        {"role": "tool", "content": "ignored"},
        {"role": "assistant", "content": "B"},
    ]

    history, question = _partition_history_and_question(messages)

    assert question == "A"
    assert history == []


def test_partition_history_returns_empty_question_when_no_user_message():
    messages = [
        {"role": "system", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]

    history, question = _partition_history_and_question(messages)

    assert question == ""
    assert history == [
        {"role": "system", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]

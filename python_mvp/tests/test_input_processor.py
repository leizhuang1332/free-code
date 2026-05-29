from app.input_processor import process_user_input


def test_process_user_input_turns_plain_text_into_user_message():
    processed = process_user_input("hello")

    assert processed.should_query is True
    assert processed.clear_messages is False
    assert processed.local_output is None
    assert processed.messages[0].role == "user"
    assert processed.messages[0].content == "hello"


def test_process_user_input_help_is_local_command():
    processed = process_user_input("/help")

    assert processed.should_query is False
    assert processed.local_output == "Commands: /help, /clear, /exit"
    assert processed.messages == []


def test_process_user_input_clear_is_local_command_with_clear_intent():
    processed = process_user_input("/clear")

    assert processed.should_query is False
    assert processed.clear_messages is True
    assert processed.local_output == "Conversation cleared."

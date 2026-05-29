from app.messages import Message, ToolUse
from app.model_client import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DeepSeekOpenAIClient,
    chat_message_to_assistant_turn,
    messages_to_chat_messages,
    tool_schemas_to_chat_tools,
)


def test_messages_to_chat_messages_converts_roles_and_tool_results():
    messages = [
        Message(role="user", content="read README.md"),
        Message(
            role="assistant",
            content="",
            tool_uses=[ToolUse(id="call_1", name="read_file", input={"path": "README.md"})],
        ),
        Message(
            role="tool",
            content="file contents",
            tool_call_id="call_1",
            tool_name="read_file",
        ),
    ]

    converted = messages_to_chat_messages(messages)

    assert converted[0] == {"role": "user", "content": "read README.md"}
    assert converted[1]["role"] == "assistant"
    assert converted[1]["content"] == ""
    assert converted[1]["tool_calls"][0]["id"] == "call_1"
    assert converted[1]["tool_calls"][0]["function"]["name"] == "read_file"
    assert converted[2] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "file contents",
    }


def test_tool_schemas_to_chat_tools_converts_input_schema_to_parameters():
    schemas = [
        {
            "name": "read_file",
            "description": "Read a file.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }
    ]

    converted = tool_schemas_to_chat_tools(schemas)

    assert converted == [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file.",
                "parameters": schemas[0]["input_schema"],
            },
        }
    ]


def test_chat_message_to_assistant_turn_parses_text_and_tool_calls():
    message = {
        "content": "Need a file.",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": '{"path": "README.md"}',
                },
            }
        ],
    }

    turn = chat_message_to_assistant_turn(message)

    assert turn.text == "Need a file."
    assert turn.tool_uses[0].id == "call_1"
    assert turn.tool_uses[0].name == "read_file"
    assert turn.tool_uses[0].input == {"path": "README.md"}


class FakeChatCompletions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        message = type("FakeMessage", (), {"content": "ok", "tool_calls": []})()
        choice = type("FakeChoice", (), {"message": message})()
        return type("FakeResponse", (), {"choices": [choice]})()


class FakeChat:
    def __init__(self):
        self.completions = FakeChatCompletions()


class FakeOpenAI:
    def __init__(self):
        self.chat = FakeChat()


def test_deepseek_client_calls_chat_completions_with_model_messages_and_tools():
    sdk = FakeOpenAI()
    client = DeepSeekOpenAIClient(client=sdk, model="deepseek-test")

    turn = client.complete(
        system_prompt="You are helpful.",
        messages=[Message(role="user", content="hi")],
        tools=[{"name": "echo", "description": "Echo", "input_schema": {"type": "object"}}],
    )

    assert turn.text == "ok"
    assert sdk.chat.completions.kwargs["model"] == "deepseek-test"
    assert sdk.chat.completions.kwargs["messages"] == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "hi"},
    ]
    assert sdk.chat.completions.kwargs["tools"][0]["function"]["name"] == "echo"


def test_deepseek_client_from_env_uses_deepseek_defaults(monkeypatch):
    captured = {}

    class CapturingOpenAI:
        def __init__(self, api_key, base_url):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            self.chat = FakeChat()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "key")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)

    client = DeepSeekOpenAIClient.from_env(openai_factory=CapturingOpenAI)

    assert client.model == DEEPSEEK_MODEL
    assert captured == {"api_key": "key", "base_url": DEEPSEEK_BASE_URL}

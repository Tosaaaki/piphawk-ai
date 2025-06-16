import backend.utils.openai_client as oc


def test_trim_tokens_limit():
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "x" * 50000},
        {"role": "assistant", "content": "y" * 50000},
    ]
    trimmed = oc.trim_tokens(messages, limit=1000)
    assert oc.num_tokens(trimmed) <= 1000
    assert trimmed[0]["role"] == "system"


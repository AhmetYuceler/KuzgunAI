from kuzgun.verify import check_python_syntax, extract_code_blocks


def test_extract_python_block():
    text = "İşte kod:\n```python\ndef f():\n    return 1\n```\nbitti"
    blocks = extract_code_blocks(text)
    assert len(blocks) == 1
    assert "def f()" in blocks[0]


def test_extract_bare_block():
    text = "```\nx = 1\n```"
    assert extract_code_blocks(text) == ["x = 1"]


def test_extract_no_block():
    assert extract_code_blocks("sadece düz metin") == []


def test_valid_syntax():
    ok, err = check_python_syntax("def f():\n    return 1")
    assert ok is True
    assert err is None


def test_invalid_syntax_reports_error():
    ok, err = check_python_syntax("def f(:\n    return")
    assert ok is False
    assert err  # hata mesajı dolu

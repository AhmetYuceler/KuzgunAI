from kuzgun.embeddings import cosine, FakeEmbedder


def test_cosine_identical_is_one():
    assert abs(cosine([1, 2, 3], [1, 2, 3]) - 1.0) < 1e-9


def test_cosine_orthogonal_is_zero():
    assert cosine([1, 0], [0, 1]) == 0.0


def test_cosine_empty_is_zero():
    assert cosine([], [1, 2]) == 0.0


def test_fake_embedder_deterministic():
    e = FakeEmbedder()
    assert e.embed("test") == e.embed("test")


def test_fake_embedder_similar_text_scores_higher():
    e = FakeEmbedder()
    a = e.embed("merhaba dunya")
    b = e.embed("merhaba dunya nasilsin")
    c = e.embed("zzzz qqqq")
    assert cosine(a, b) > cosine(a, c)


def test_ollama_embedder_has_short_timeout():
    from kuzgun.embeddings import OllamaEmbedder

    assert 0 < OllamaEmbedder().client_timeout <= 60

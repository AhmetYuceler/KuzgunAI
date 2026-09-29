from kuzgun.router import classify_complexity


def test_hard_tasks_classified_zor():
    for msg in [
        "Bana bir React uygulaması kur",
        "vite ile proje oluştur",
        "npm install yap ve çalıştır",
        "şu kodu baştan refactor et",
    ]:
        level, reason = classify_complexity(msg)
        assert level == "zor", msg
        assert reason


def test_easy_tasks_classified_kolay():
    for msg in [
        "Merhaba, nasılsın?",
        "Fransa'nın başkenti neresi?",
        "2 + 2 kaç eder?",
    ]:
        level, reason = classify_complexity(msg)
        assert level == "kolay", msg
        assert reason is None

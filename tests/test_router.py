from kuzgun.router import classify_complexity, is_code_task


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


def test_code_tasks_detected():
    for msg in [
        "Python'da iki sayiyi toplayan bir fonksiyon yaz",
        "şu javascript kodundaki sorunu bul",
        "bir SQL sorgusu yaz",
        "bu algoritmayı optimize et",
        "şu .py dosyasını incele",
    ]:
        assert is_code_task(msg), msg


def test_non_code_tasks_not_detected():
    for msg in ["Merhaba nasılsın", "Fransa'nın başkenti neresi", "bugün hava nasıl"]:
        assert not is_code_task(msg), msg

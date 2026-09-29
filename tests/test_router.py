from kuzgun.router import (
    classify_complexity,
    detect_media_intent,
    detect_weather_intent,
    is_code_task,
)


def test_detect_weather_intent():
    assert detect_weather_intent("bugün hava durumu nedir")
    assert detect_weather_intent("dışarıda hava nasıl")
    assert detect_weather_intent("kaç derece bugün")
    assert not detect_weather_intent("bana bir şarkı çal")
    assert not detect_weather_intent("Fransa'nın başkenti")


def test_detect_media_intent():
    assert detect_media_intent("spotifydan müziği değiştir") == "next"
    assert detect_media_intent("sonraki şarkıya geç") == "next"
    assert detect_media_intent("önceki şarkı") == "previous"
    assert detect_media_intent("müziği durdur") == "playpause"
    assert detect_media_intent("sesi aç") == "volup"


def test_detect_media_intent_none_for_normal():
    assert detect_media_intent("Fransa'nın başkenti neresi") is None
    assert detect_media_intent("bana bir fonksiyon yaz") is None


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


def test_is_compound_detects_multiple_questions():
    from kuzgun.router import is_compound

    assert is_compound("hava kaç derece şu anda? 2x2 kaç? türkiye başkenti neresi")
    assert is_compound("hava nasıl. bir de şu dosyayı oku")
    assert not is_compound("bugün hava nasıl?")
    assert not is_compound("hava kaç derece, yağmur var mı?")  # tek soru, virgüllü

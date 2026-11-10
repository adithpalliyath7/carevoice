from app.nlu import parse

def test_book_cardiology_tomorrow():
    p = parse("Book a cardiology appointment tomorrow at 10 am")
    assert p["intent"] == "book"
    assert p["speciality"] == "cardiology"
    assert p["time"] == "10:00"
    assert p["confidence"] >= 0.8
    assert not p["needs_clarification"]

def test_search_without_speciality_asks():
    p = parse("I need a doctor")
    assert p["needs_clarification"] is True
    assert p["clarification_question"]

def test_confirm_only_when_awaiting():
    p = parse("yes", session={"awaiting_confirmation": True})
    assert p["intent"] == "confirm"
    p2 = parse("yes")
    assert p2["intent"] != "confirm"

def test_emergency():
    p = parse("I have chest pain, need emergency help")
    assert p["intent"] == "emergency"

def test_gibberish_never_books():
    p = parse("asdf qwer zzz")
    assert p["intent"] == "unknown"
    assert p["confidence"] < 0.5
    assert p["needs_clarification"]

def test_repeat_and_time_formats():
    assert parse("please repeat slowly")["intent"] == "repeat"
    assert parse("book dental at 2:30 pm")["time"] == "14:30"

def test_cancel_intent():
    p = parse("cancel my appointment")
    assert p["intent"] == "cancel"

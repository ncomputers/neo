from api.app.utils.i18n import get_text


def test_get_text_fallback():
    field = "English"
    field_i18n = {"hi": "Hindi"}
    assert get_text(field, "hi", field_i18n) == "Hindi"
    # falls back to English when translation missing
    assert get_text(field, "gu", field_i18n) == "English"
    # falls back to any available translation when English missing
    assert get_text(None, "gu", {"mr": "Marathi"}) == "Marathi"

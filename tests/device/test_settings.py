import settings


def test_get_brightness_defaults_when_no_file(tmp_path):
    path = str(tmp_path / "settings.json")
    assert settings.get_brightness(path) == settings.DEFAULT_BRIGHTNESS


def test_set_brightness_persists_and_round_trips(tmp_path):
    path = str(tmp_path / "settings.json")
    settings.set_brightness(path, 128)
    assert settings.get_brightness(path) == 128


def test_get_brightness_defaults_on_corrupt_file(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not json")
    assert settings.get_brightness(str(path)) == settings.DEFAULT_BRIGHTNESS


def test_set_brightness_preserves_other_keys(tmp_path):
    path = str(tmp_path / "settings.json")
    settings.save(path, {"other": "value"})
    settings.set_brightness(path, 64)
    assert settings.load(path) == {"other": "value", "brightness": 64}

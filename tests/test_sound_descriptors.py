from sound_descriptors import descriptor_hints


def test_russian_dark_hard_distorted():
    hints = descriptor_hints("тёмный жёсткий дисторшн бас", style="opium")
    assert "dist" in hints
    assert "dark" in hints
    assert "hard" in hints


def test_english_bright_bell():
    hints = descriptor_hints("glassy bright bell melody")
    assert "bell" in hints
    assert "glass" in hints


def test_empty_prompt_no_hints():
    assert descriptor_hints("") == ()


def test_vintage_lofi():
    hints = descriptor_hints("винтажный пыльный сэмпл", style="")
    assert "vintage" in hints

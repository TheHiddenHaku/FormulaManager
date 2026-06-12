"""Test segnaposto del motore: il pacchetto esiste ed e' importabile."""

import fm_engine


def test_fm_engine_importable():
    assert fm_engine.__doc__ is not None


def test_fm_engine_has_version():
    assert isinstance(fm_engine.__version__, str)
    assert fm_engine.__version__

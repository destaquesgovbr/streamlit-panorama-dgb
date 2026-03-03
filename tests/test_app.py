"""Basic tests for the Panorama Gov.BR application"""

import pytest


def test_app_version():
    """Test that the app has a version"""
    import app
    assert hasattr(app, '__version__')
    assert app.__version__ == "0.1.0"


def test_utils_fmt_number():
    """Test number formatting"""
    from app.utils import fmt_number
    assert fmt_number(1234) == "1.234"
    assert fmt_number(0) == "0"


def test_utils_fmt_pct():
    """Test percentage formatting"""
    from app.utils import fmt_pct
    assert fmt_pct(10.5) == "+10.5%"
    assert fmt_pct(-3.2) == "-3.2%"

import pytest
from app.services.drivers import determine_driver_count

def test_determine_driver_count_3():
    scores = {
        'market': 0.8,
        'sector': 0.5,
        'filings': 0.3,
        'insider': 0.2,
        'flow_technical': 0.4
    }
    assert determine_driver_count(scores) == 3

def test_determine_driver_count_5_strong():
    scores = {
        'market': 0.8,
        'sector': 0.7,
        'filings': 0.65,
        'insider': 0.9,
        'flow_technical': 0.75
    }
    assert determine_driver_count(scores) == 5

def test_determine_driver_count_5_mixed():
    scores = {
        'market': 0.8,
        'sector': 0.7,
        'filings': 0.65,
        'insider': 0.5,
        'flow_technical': 0.45
    }
    assert determine_driver_count(scores) == 5


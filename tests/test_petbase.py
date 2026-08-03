import pytest
from tuipet.core.petbase import Refused, _clamp, _enemy_level, _weekend_mult, online_reward, weekend_bonus
import datetime

def test_refused():
    r = Refused("No way")
    assert r == "No way"
    assert isinstance(r, str)
    assert isinstance(r, Refused)

def test_clamp():
    assert _clamp(10, 0, 100) == 10
    assert _clamp(-10, 0, 100) == 0
    assert _clamp(110, 0, 100) == 100

def test_enemy_level():
    assert _enemy_level({"stage": "Rookie"}) == 3
    assert _enemy_level({"stage": "Fresh"}) == 1
    assert _enemy_level({}) == 3

def test_weekend_bonus():
    mon = datetime.datetime(2026, 8, 3).timestamp() # Monday
    sat = datetime.datetime(2026, 8, 8).timestamp() # Saturday
    
    assert _weekend_mult(now=mon) == 1.0
    assert _weekend_mult(now=sat) == 1.5

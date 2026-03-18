"""Tests for Vidya."""
from src.core import Vidya
def test_init(): assert Vidya().get_stats()["ops"] == 0
def test_op(): c = Vidya(); c.detect(x=1); assert c.get_stats()["ops"] == 1
def test_multi(): c = Vidya(); [c.detect() for _ in range(5)]; assert c.get_stats()["ops"] == 5
def test_reset(): c = Vidya(); c.detect(); c.reset(); assert c.get_stats()["ops"] == 0
def test_service_name(): c = Vidya(); r = c.detect(); assert r["service"] == "vidya"

import importlib
import types
import sys

import pytest


def load_module(monkeypatch):
    class DummyInfluxDBClient:
        def __init__(self, *a, **kw):
            pass
        def switch_database(self, *a, **kw):
            pass
        def write_points(self, *a, **kw):
            pass
    class DummyInfluxDBClient3:
        def __init__(self, *a, **kw):
            pass
        def write(self, record=None):
            pass

    import influxdb
    import influxdb_client_3
    monkeypatch.setattr(influxdb, 'InfluxDBClient', DummyInfluxDBClient)
    monkeypatch.setattr(influxdb_client_3, 'InfluxDBClient3', DummyInfluxDBClient3)

    module = importlib.import_module('garmin_grafana.garmin_fetch')
    return module

class DummyGarmin:
    def __init__(self, stats=None, hr=None):
        self._stats = stats or {}
        self._hr = hr or []

    def get_stats(self, date):
        return self._stats

    def get_heart_rates(self, date):
        return {'heartRateValues': self._hr}


def test_iter_days(monkeypatch):
    module = load_module(monkeypatch)
    days = list(module.iter_days('2024-01-01', '2024-01-03'))
    assert days == ['2024-01-03', '2024-01-02', '2024-01-01']


def test_get_daily_stats(monkeypatch):
    module = load_module(monkeypatch)
    sample = {
        'wellnessStartTimeGmt': '2024-06-01T00:00:00.000',
        'activeKilocalories': 10,
        'bmrKilocalories': 20,
        'totalSteps': 1000,
        'totalDistanceMeters': 500.0,
    }
    monkeypatch.setattr(module, 'garmin_obj', DummyGarmin(stats=sample))
    monkeypatch.setattr(module, 'GARMIN_DEVICENAME', 'dev')
    monkeypatch.setattr(module, 'INFLUXDB_DATABASE', 'db')
    pts = module.get_daily_stats('2024-06-01')
    assert len(pts) == 1
    p = pts[0]
    assert p['measurement'] == 'DailyStats'
    assert p['tags']['Device'] == 'dev'
    assert p['fields']['activeKilocalories'] == 10


def test_get_intraday_hr(monkeypatch):
    module = load_module(monkeypatch)
    hr = [
        [1700000000000, 60],
        [1700000005000, 61],
    ]
    monkeypatch.setattr(module, 'garmin_obj', DummyGarmin(hr=hr))
    monkeypatch.setattr(module, 'GARMIN_DEVICENAME', 'dev')
    monkeypatch.setattr(module, 'INFLUXDB_DATABASE', 'db')
    pts = module.get_intraday_hr('2024-06-01')
    assert len(pts) == 2
    assert pts[0]['fields']['HeartRate'] == 60

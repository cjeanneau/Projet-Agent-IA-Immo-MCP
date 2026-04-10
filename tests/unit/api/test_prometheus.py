import pytest
from unittest.mock import MagicMock, patch
from src.app.monitoring.prometheus_metrics import track_inference_time, setup_prometheus


@pytest.mark.unit
class TestPrometheusMetrics:
    def test_track_inference_time(self):
        track_inference_time(150.5)
        track_inference_time(0.0)
        track_inference_time(9999.9)

    def test_setup_prometheus(self):
        mock_app = MagicMock()
        setup_prometheus(mock_app)

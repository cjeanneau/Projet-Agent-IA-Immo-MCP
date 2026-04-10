import pytest
import pickle
import tempfile
from pathlib import Path
from src.utils.load_models import load_pickle


@pytest.mark.unit
class TestLoadPickle:
    def test_loads_pickled_object(self, tmp_path):
        data = {"key": "value", "number": 42}
        model_path = tmp_path / "model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(data, f)

        result = load_pickle(model_path)
        assert result == data

    def test_loads_with_string_path(self, tmp_path):
        data = [1, 2, 3]
        model_path = tmp_path / "model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(data, f)

        result = load_pickle(str(model_path))
        assert result == data

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_pickle("/tmp/nonexistent_model.pkl")

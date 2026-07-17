from garmin_running_data_normalizer import IMPLEMENTATION_STATUS, __version__


def test_bootstrap_identity() -> None:
    assert __version__ == "0.0.0"
    assert IMPLEMENTATION_STATUS == "BOOTSTRAP_ONLY"


import pytest

from macro_data_platform.services.validation import DataValidationError, validate_observations


def test_validation_rejects_duplicate_dates() -> None:
    observations = [
        {"date": "2024-01-01", "value": "1.0"},
        {"date": "2024-01-01", "value": "2.0"},
    ]
    with pytest.raises(DataValidationError, match="duplicate source date"):
        validate_observations("TEST", observations)


def test_validation_allows_missing_values() -> None:
    validate_observations("TEST", [{"date": "2024-01-01", "value": None}])


def test_validation_rejects_non_numeric_values() -> None:
    with pytest.raises(DataValidationError, match="invalid value"):
        validate_observations("TEST", [{"date": "2024-01-01", "value": "not-a-number"}])

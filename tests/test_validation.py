from vortexify import (
    ValidationIssue,
    ValidationResult,
)


def test_validation_result_is_valid_without_issues():
    result = ValidationResult()

    assert result.valid is True
    assert result.issues == []


def test_validation_error_makes_result_invalid():
    result = ValidationResult(
        issues=[
            ValidationIssue(
                message=(
                    "Quantity cannot be negative."
                ),
            ),
        ],
    )

    assert result.valid is False


def test_validation_warning_does_not_make_result_invalid():
    result = ValidationResult(
        issues=[
            ValidationIssue(
                message=(
                    "Quantity is unusually high."
                ),
                level="warning",
            ),
        ],
    )

    assert result.valid is True


def test_validation_issue_defaults():
    issue = ValidationIssue(
        message="Invalid quantity.",
    )

    assert issue.level == "error"
    assert issue.code is None
    assert issue.field is None


def test_validation_issue_structured_fields():
    issue = ValidationIssue(
        message="Quantity cannot be negative.",
        level="error",
        code="negative_quantity",
        field="quantity",
    )

    assert issue.message == (
        "Quantity cannot be negative."
    )
    assert issue.level == "error"
    assert issue.code == "negative_quantity"
    assert issue.field == "quantity"


def test_warning_and_error_result_is_invalid():
    result = ValidationResult(
        issues=[
            ValidationIssue(
                message="Quantity is unusually high.",
                level="warning",
            ),
            ValidationIssue(
                message="Quantity cannot be negative.",
                level="error",
            ),
        ],
    )

    assert result.valid is False

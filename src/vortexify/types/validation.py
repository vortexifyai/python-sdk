from typing import Literal

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """
    Describes a single issue found while validating a resource output.
    """

    message: str
    """
    Human-readable description of the validation issue.
    """

    level: Literal[
        "error",
        "warning",
    ] = "error"
    """
    Severity of the issue.

    `error` causes the ValidationResult to be invalid.
    `warning` is recorded without causing validation to fail.
    """

    code: str | None = None
    """
    Optional machine-readable identifier used to categorize the issue.
    """

    field: str | None = None
    """
    Optional field or column associated with the issue.
    """


class ValidationResult(BaseModel):
    """
    Structured result returned by a Vortexify validation function.
    """

    issues: list[ValidationIssue] = Field(
        default_factory=list
    )
    """
    Validation issues found in the resource output.
    """

    @property
    def valid(self) -> bool:
        """
        Whether validation passed without any error-level issues.
        """
        return not any(
            issue.level == "error"
            for issue in self.issues
        )

"""
Test Python document for CCS-7 placeholder.
"""

from typing import Final

CCS_CODE: Final[str] = "CCS-7"


def get_ccs_code() -> str:
    """Return the CCS identifier code used for testing."""
    return CCS_CODE


def test_ccs_code_is_correct() -> None:
    """A trivial test to validate the CCS code value."""
    assert get_ccs_code() == "CCS-7"


if __name__ == "__main__":
    print(get_ccs_code())

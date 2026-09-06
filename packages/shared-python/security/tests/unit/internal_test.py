# tests internal
from security import matches_internal_key


class TestMatchesInternalKey:
    # verifies that accepts the expected key
    def test_accepts_the_expected_key(self) -> None:
        assert matches_internal_key("s3cret", "s3cret") is True

    # verifies that rejects a different key
    def test_rejects_a_different_key(self) -> None:
        assert matches_internal_key("other", "s3cret") is False

    # verifies that rejects an unset expectation
    def test_rejects_an_unset_expectation(self) -> None:
        assert matches_internal_key("", "") is False
        assert matches_internal_key("anything", "") is False

    # verifies that rejects an absent candidate
    def test_rejects_an_absent_candidate(self) -> None:
        assert matches_internal_key("", "s3cret") is False

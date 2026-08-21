from security import matches_internal_key


class TestMatchesInternalKey:
    def test_accepts_the_expected_key(self) -> None:
        assert matches_internal_key("s3cret", "s3cret") is True

    def test_rejects_a_different_key(self) -> None:
        assert matches_internal_key("other", "s3cret") is False

    def test_rejects_an_unset_expectation(self) -> None:
        assert matches_internal_key("", "") is False
        assert matches_internal_key("anything", "") is False

    def test_rejects_an_absent_candidate(self) -> None:
        assert matches_internal_key("", "s3cret") is False

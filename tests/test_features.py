from blunder_tutor.features import DEFAULTS, FEATURE_LABELS, Feature


class TestReviewEngineFeature:
    def test_flag_exists_and_defaults_off(self):
        assert Feature.REVIEW_ENGINE.value == "review.engine"
        assert DEFAULTS[Feature.REVIEW_ENGINE] is False

    def test_flag_has_label(self):
        assert (
            FEATURE_LABELS[Feature.REVIEW_ENGINE] == "settings.features.review_engine"
        )

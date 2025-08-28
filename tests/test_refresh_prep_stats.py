from scripts.refresh_prep_stats import summarize


def test_summarize_quantiles():
    samples = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    stats = summarize(samples)
    assert stats["p50_s"] == 5
    assert stats["sample_n"] == 10


def test_summarize_min_samples():
    assert summarize([1, 2, 3]) is None

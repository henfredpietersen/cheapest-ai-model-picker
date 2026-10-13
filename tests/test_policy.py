from router.policy import route


def test_easy_stays_local():
    assert route("easy", budget_usd=0.001).name == "local-4bit"


def test_hard_pays_for_quality():
    assert route("hard", budget_usd=1.0).name == "hosted-large"


def test_normal_picks_small_when_budget_allows():
    assert route("normal", budget_usd=0.05).name == "hosted-small"

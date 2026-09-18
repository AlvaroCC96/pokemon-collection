from app.providers.price.base import PriceObservationResult
from app.services import price_service


def _obs(price, currency="CLP", region="CHILE", source="x", confidence=None, language=None):
    return PriceObservationResult(
        source_name=source,
        source_url="https://example.com",
        observed_price=price,
        currency=currency,
        market_region=region,
        matched_confidence=confidence,
        language=language,
    )


def test_select_market_group_prefers_chile() -> None:
    obs = [_obs(100, region="INTERNATIONAL"), _obs(200, region="CHILE")]
    scope, group = price_service._select_market_group(obs)
    assert scope == "CHILE"
    assert len(group) == 1


def test_select_market_group_falls_back_to_international() -> None:
    obs = [_obs(100, region="INTERNATIONAL"), _obs(200, region="INTERNATIONAL")]
    scope, group = price_service._select_market_group(obs)
    assert scope == "INTERNATIONAL"
    assert len(group) == 2


def test_select_market_group_returns_none_when_empty() -> None:
    scope, group = price_service._select_market_group([])
    assert scope is None
    assert group is None


def test_select_currency_group_picks_dominant_currency() -> None:
    obs = [_obs(100, currency="USD"), _obs(200, currency="USD"), _obs(50, currency="EUR")]
    currency, group = price_service._select_currency_group(obs)
    assert currency == "USD"
    assert len(group) == 2


def test_mark_outliers_flags_extreme_value() -> None:
    flags = price_service._mark_outliers([100, 110, 90, 5000])
    assert flags == [False, False, False, True]


def test_mark_outliers_no_flags_for_similar_prices() -> None:
    flags = price_service._mark_outliers([100, 105, 95])
    assert flags == [False, False, False]


def test_confidence_score_higher_with_more_sources_and_low_dispersion() -> None:
    few = [_obs(100)]
    many = [_obs(100), _obs(105), _obs(98)]
    assert price_service._confidence_score(many, "CHILE") > price_service._confidence_score(
        few, "CHILE"
    )


def test_confidence_score_penalizes_international_scope() -> None:
    obs = [_obs(100), _obs(105), _obs(98)]
    chile_score = price_service._confidence_score(obs, "CHILE")
    intl_score = price_service._confidence_score(obs, "INTERNATIONAL")
    assert intl_score < chile_score


def test_confidence_label_thresholds() -> None:
    assert price_service._confidence_label(0.9) == "HIGH"
    assert price_service._confidence_label(0.5) == "MEDIUM"
    assert price_service._confidence_label(0.1) == "LOW"


def test_select_language_group_returns_all_when_card_language_unset() -> None:
    obs = [_obs(100, language="ES"), _obs(200, language="EN"), _obs(300, language=None)]
    result = price_service._select_language_group(obs, None)
    assert result == obs


def test_select_language_group_keeps_matching_and_unknown_language() -> None:
    obs = [
        _obs(100, language="ES", source="a"),
        _obs(200, language="EN", source="b"),
        _obs(300, language=None, source="c"),
    ]
    result = price_service._select_language_group(obs, "ES")
    assert {o.source_name for o in result} == {"a", "c"}


def test_select_language_group_matches_full_language_name() -> None:
    obs = [_obs(100, language="Español"), _obs(200, language="Inglés")]
    result = price_service._select_language_group(obs, "ES")
    assert len(result) == 1
    assert result[0].language == "Español"


def test_select_language_group_empty_when_all_other_language() -> None:
    obs = [_obs(100, language="EN"), _obs(200, language="JP")]
    result = price_service._select_language_group(obs, "ES")
    assert result == []


def test_language_matches_ingles_without_accent_equals_en() -> None:
    # regression: "Ingles" and "EN" share no 2-letter prefix ("in" vs "en"),
    # a naive prefix comparison used to reject this pairing entirely.
    assert price_service._language_matches("EN", "Ingles") is True
    assert price_service._language_matches("EN", "ingles") is True
    assert price_service._language_matches("EN", "Inglés") is True
    assert price_service._language_matches("EN", "English") is True


def test_language_matches_espanol_variants_equal_es() -> None:
    assert price_service._language_matches("ES", "Español") is True
    assert price_service._language_matches("ES", "espanol") is True
    assert price_service._language_matches("ES", "Spanish") is True


def test_language_matches_still_rejects_different_language() -> None:
    assert price_service._language_matches("EN", "Español") is False
    assert price_service._language_matches("JP", "Ingles") is False


def test_select_language_group_with_ingles_keeps_en_observations() -> None:
    obs = [_obs(100, language="EN", source="a"), _obs(200, language="ES", source="b")]
    result = price_service._select_language_group(obs, "Ingles")
    assert {o.source_name for o in result} == {"a"}


def test_compute_price_change_positive() -> None:
    change = price_service._compute_price_change(110, 100, "CLP")
    assert change.previous_price == 100
    assert change.price_change == 10
    assert change.price_change_percent == 10.0


def test_compute_price_change_negative() -> None:
    change = price_service._compute_price_change(90, 100, "CLP")
    assert change.previous_price == 100
    assert change.price_change == -10
    assert change.price_change_percent == -10.0


def test_compute_price_change_none_when_no_previous() -> None:
    change = price_service._compute_price_change(100, None, "CLP")
    assert change.previous_price is None
    assert change.price_change is None
    assert change.price_change_percent is None

from app.providers.identification.base import IdentificationQuery
from app.providers.identification.pokemon_tcg_io import PokemonTCGIOProvider, _normalize_number


def test_build_query_uses_number_before_slash() -> None:
    query = IdentificationQuery(name="Charizard ex", collector_number="199/165")
    built = PokemonTCGIOProvider._build_query(query, query.name)
    assert built == 'name:"Charizard ex" number:199'


def test_build_query_uses_number_as_is_without_slash() -> None:
    query = IdentificationQuery(name="Pikachu", collector_number="25")
    built = PokemonTCGIOProvider._build_query(query, query.name)
    assert built == 'name:"Pikachu" number:25'


def test_build_query_includes_set_name_when_provided() -> None:
    query = IdentificationQuery(name="Charizard ex", collector_number="199/165", set_name="151")
    built = PokemonTCGIOProvider._build_query(query, query.name)
    assert built == 'name:"Charizard ex" number:199 set.name:"151"'


def test_build_query_ignores_language() -> None:
    query = IdentificationQuery(name="Pikachu", collector_number="25", language="Español")
    built = PokemonTCGIOProvider._build_query(query, query.name)
    assert "Español" not in built


def test_build_query_uses_provided_name_override() -> None:
    query = IdentificationQuery(name="Charizard GX", collector_number="20")
    built = PokemonTCGIOProvider._build_query(query, "Charizard-GX")
    assert built == 'name:"Charizard-GX" number:20'


def test_spacing_variants_space_to_hyphen() -> None:
    # pokemontcg.io stores "Charizard-GX" (hyphen) even though that's an
    # unnatural way to type it.
    assert PokemonTCGIOProvider._spacing_variants("Charizard GX") == ["Charizard-GX"]


def test_spacing_variants_hyphen_to_space() -> None:
    # ...but stores "Charizard VMAX" with a space, the opposite convention.
    assert PokemonTCGIOProvider._spacing_variants("Charizard-VMAX") == ["Charizard VMAX"]


def test_spacing_variants_none_when_no_space_or_hyphen() -> None:
    assert PokemonTCGIOProvider._spacing_variants("Pikachu") == []


def test_spacing_variants_never_repeats_the_original() -> None:
    assert "Charizard GX" not in PokemonTCGIOProvider._spacing_variants("Charizard GX")


def test_normalize_number_strips_leading_zeros() -> None:
    # regression: pokemontcg.io stores "74", not "074", even for secret
    # rares printed on the card as "074/073".
    assert _normalize_number("074/073") == "74"
    assert _normalize_number("004") == "4"


def test_normalize_number_leaves_plain_numbers_unchanged() -> None:
    assert _normalize_number("199/165") == "199"
    assert _normalize_number("25") == "25"


def test_normalize_number_leaves_alphanumeric_codes_unchanged() -> None:
    assert _normalize_number("SWSH261") == "SWSH261"


def test_normalize_number_all_zeros_falls_back_to_zero() -> None:
    assert _normalize_number("00") == "0"

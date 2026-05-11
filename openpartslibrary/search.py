"""Search normalization, synonym expansion, and part ranking logic."""

import json
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path


SYNONYM_GROUPS_PATH = Path(__file__).with_name("search_synonyms.json")


@lru_cache(maxsize=50000)
def normalize_search_text(value):
    """Normalize text for fuzzy and token-based search matching."""

    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.lower()
    value = re.sub(r"([a-z])(\d)", r"\1 \2", value)
    value = re.sub(r"(\d)([a-z])", r"\1 \2", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def build_synonyms(groups):
    """Build a lookup of normalized terms to equivalent normalized terms."""

    synonyms = {}
    for group in groups:
        normalized_group = {normalize_search_text(term) for term in group if term}
        for term in normalized_group:
            synonyms.setdefault(term, set()).update(normalized_group - {term})
    return synonyms


def normalize_synonym_group(raw_group):
    if isinstance(raw_group, dict):
        raw_terms = raw_group.get("terms", [])
    else:
        raw_terms = raw_group

    if not isinstance(raw_terms, list):
        return set()

    return {
        str(term).strip()
        for term in raw_terms
        if str(term).strip()
    }


def normalize_term_list(value):
    if not isinstance(value, list):
        return set()

    return {
        normalize_search_text(term)
        for term in value
        if normalize_search_text(term)
    }


def normalize_ranking_rule(rule):
    return {
        "name": str(rule.get("name", "")),
        "query_terms": normalize_term_list(rule.get("query_terms", [])),
        "boost_name_terms": normalize_term_list(rule.get("boost_name_terms", [])),
        "demote_name_terms": normalize_term_list(rule.get("demote_name_terms", [])),
        "boost_score": int(rule.get("boost_score", 124)),
        "demote_score": int(rule.get("demote_score", 90)),
    }


def load_search_config():
    """Load synonym groups and ranking rules from ``search_synonyms.json``."""

    try:
        with SYNONYM_GROUPS_PATH.open("r", encoding="utf-8") as synonyms_file:
            data = json.load(synonyms_file)
    except (OSError, json.JSONDecodeError):
        return {"groups": (), "ranking_rules": ()}

    if not isinstance(data, dict):
        data = {"groups": data}

    raw_groups = data.get("groups", [])
    if not isinstance(raw_groups, list):
        raw_groups = []

    groups = tuple(
        group
        for group in (normalize_synonym_group(raw_group) for raw_group in raw_groups)
        if group
    )

    raw_rules = data.get("ranking_rules", [])
    if not isinstance(raw_rules, list):
        raw_rules = []

    return {
        "groups": groups,
        "ranking_rules": tuple(
            normalize_ranking_rule(rule)
            for rule in raw_rules
            if isinstance(rule, dict)
        ),
    }


def synonym_groups_signature():
    try:
        return SYNONYM_GROUPS_PATH.stat().st_mtime_ns
    except OSError:
        return 0


@lru_cache(maxsize=8)
def get_search_config(_signature):
    return load_search_config()


def get_synonyms(signature):
    return build_synonyms(get_search_config(signature)["groups"])


def get_ranking_rules(signature):
    return get_search_config(signature)["ranking_rules"]


def query_phrases(normalized_query, max_words=4):
    tokens = normalized_query.split()
    phrases = {normalized_query} if normalized_query else set()
    for start_index in range(len(tokens)):
        for end_index in range(start_index + 1, min(len(tokens), start_index + max_words) + 1):
            phrase = " ".join(tokens[start_index:end_index])
            if len(phrase) > 1 or phrase.isdigit():
                phrases.add(phrase)
    return {phrase for phrase in phrases if phrase and (len(phrase) > 1 or phrase.isdigit())}


def expand_query_terms(query):
    """Return direct and synonym-expanded search terms for a query."""

    normalized_query = normalize_search_text(query)
    direct_terms = {normalized_query} if normalized_query else set()
    synonym_terms = set()

    for phrase in query_phrases(normalized_query):
        direct_terms.add(phrase)
        synonym_terms.update(get_synonyms(synonym_groups_signature()).get(phrase, set()))

    return (
        {term for term in direct_terms if term},
        {term for term in synonym_terms if term and term not in direct_terms},
    )


def searchable_part_fields(part):
    """Return the component fields that participate in search ranking."""

    supplier_name = part.supplier.name if part.supplier else ""
    return {
        "number": part.number,
        "name": part.name,
        "description": part.description,
        "supplier": supplier_name,
        "material": part.material,
        "currency": part.currency,
        "revision": part.revision,
        "lifecycle_state": part.lifecycle_state,
        "owner": part.owner,
    }


@lru_cache(maxsize=50000)
def fuzzy_ratio(query, text):
    """Return a full-string fuzzy score from 0 to 100."""

    query = normalize_search_text(query)
    text = normalize_search_text(text)
    if not query or not text:
        return 0

    return int(SequenceMatcher(None, query, text).ratio() * 100)


@lru_cache(maxsize=50000)
def partial_fuzzy_ratio(query, text):
    """Return the best token-window fuzzy score from 0 to 100."""

    query = normalize_search_text(query)
    text = normalize_search_text(text)
    if not query or not text:
        return 0
    if query in text:
        return 100

    query_tokens = query.split()
    text_tokens = text.split()
    if not query_tokens or not text_tokens:
        return 0

    best_ratio = max(fuzzy_ratio(query, token) for token in text_tokens)
    if len(query_tokens) == 1:
        return best_ratio

    window_size = len(query_tokens)
    for index in range(0, len(text_tokens) - window_size + 1):
        window = " ".join(text_tokens[index:index + window_size])
        best_ratio = max(best_ratio, fuzzy_ratio(query, window))
        if best_ratio == 100:
            break

    return best_ratio


@lru_cache(maxsize=50000)
def token_overlap_score(query, text):
    """Return percentage overlap between query tokens and text tokens."""

    query_tokens = set(normalize_search_text(query).split())
    text_tokens = set(normalize_search_text(text).split())
    if not query_tokens or not text_tokens:
        return 0

    return int((len(query_tokens & text_tokens) / len(query_tokens)) * 100)


def is_numeric_term(term):
    return bool(re.fullmatch(r"\d+", normalize_search_text(term)))


def numeric_query_terms(query):
    return [
        int(token)
        for token in normalize_search_text(query).split()
        if token.isdigit()
    ]


def part_numeric_values(part):
    fields = searchable_part_fields(part)
    text = " ".join(
        normalize_search_text(value)
        for value in (fields.get("name"), fields.get("number"), fields.get("description"))
        if value
    )
    return [int(value) for value in re.findall(r"\d+", text)]


def numeric_match_sort_key(query, part):
    """Sort numeric search results by exact and nearest-size matches."""

    query_numbers = numeric_query_terms(query)
    if not query_numbers:
        return (0, 0, 0)

    part_numbers = part_numeric_values(part)
    if not part_numbers:
        return (3, 0, 0)

    sort_rows = []
    for query_number in query_numbers:
        exact_matches = [number for number in part_numbers if number == query_number]
        if exact_matches:
            sort_rows.append((0, 0))
            continue

        larger_or_equal = [number for number in part_numbers if number >= query_number]
        if larger_or_equal:
            sort_rows.append((1, min(larger_or_equal) - query_number))
            continue

        sort_rows.append((2, query_number - max(part_numbers)))

    return max(row[0] for row in sort_rows), sum(row[1] for row in sort_rows), len(part_numbers)


def has_search_phrase(text, phrases):
    normalized_text = normalize_search_text(text)
    return any(phrase in normalized_text for phrase in phrases)


@lru_cache(maxsize=50000)
def term_matches_text(term, text, threshold=88):
    term = normalize_search_text(term)
    text = normalize_search_text(text)
    if not term or not text:
        return False
    if term in text:
        return True

    return partial_fuzzy_ratio(term, text) >= threshold


def score_part(query, part):
    """Calculate a relevance score for one component against a query."""

    direct_terms, synonym_terms = expand_query_terms(query)
    if not direct_terms and not synonym_terms:
        return 0

    fields = searchable_part_fields(part)
    normalized_fields = {
        name: normalize_search_text(value)
        for name, value in fields.items()
    }
    combined_text = " ".join(value for value in normalized_fields.values() if value)
    best_score = 0

    field_weights = {
        "number": 1.25,
        "name": 1.15,
        "description": 0.85,
        "supplier": 0.75,
        "material": 0.75,
        "currency": 0.45,
        "revision": 0.45,
        "lifecycle_state": 0.45,
        "owner": 0.45,
    }

    for term in direct_terms:
        for field_name, field_text in normalized_fields.items():
            if not field_text:
                continue

            score = max(
                partial_fuzzy_ratio(term, field_text),
                fuzzy_ratio(term, field_text),
                token_overlap_score(term, field_text),
            )

            if term == field_text:
                score = 100

            best_score = max(best_score, int(score * field_weights[field_name]))

    for term in synonym_terms:
        for field_name, field_text in normalized_fields.items():
            if not field_text:
                continue

            score = max(
                partial_fuzzy_ratio(term, field_text),
                fuzzy_ratio(term, field_text),
                token_overlap_score(term, field_text),
            )

            best_score = max(best_score, int(score * field_weights[field_name] * 0.78))

    original_query = normalize_search_text(query)
    original_tokens = set(original_query.split())
    text_direct_terms = {term for term in direct_terms if not is_numeric_term(term)}
    text_synonym_terms = {term for term in synonym_terms if not is_numeric_term(term)}
    numeric_direct_terms = {term for term in direct_terms if is_numeric_term(term)}
    name_text = normalized_fields.get("name", "")
    number_text = normalized_fields.get("number", "")
    description_text = normalized_fields.get("description", "")
    name_tokens = set(name_text.split())

    if original_query and original_query in name_text:
        best_score = max(best_score, 125)
    elif original_tokens and original_tokens <= set(name_text.split()):
        best_score = max(best_score, 120)

    if original_query and original_query in number_text:
        best_score = max(best_score, 122)

    direct_type_match = any(
        term_matches_text(term, name_text) or term_matches_text(term, description_text)
        for term in text_direct_terms
    )
    synonym_type_match = any(
        term_matches_text(term, name_text) or term_matches_text(term, description_text)
        for term in text_synonym_terms
    )

    if direct_type_match:
        best_score = max(best_score, 124)
    elif synonym_type_match:
        best_score = max(best_score, 116)

    numeric_specifier_match = bool(numeric_direct_terms & name_tokens)
    if (direct_type_match or synonym_type_match) and numeric_specifier_match:
        best_score = min(125, best_score + 6)

    if text_direct_terms and not direct_type_match and not synonym_type_match:
        # A specifier like "1200" should not outrank the requested part type.
        best_score = min(best_score, 92)

    name_has_direct_type_match = any(term_matches_text(term, name_text) for term in text_direct_terms)
    name_has_synonym_type_match = any(term_matches_text(term, name_text) for term in text_synonym_terms)
    if text_direct_terms and not name_has_direct_type_match and not name_has_synonym_type_match:
        # Description-only matches are relevant, but should not beat parts whose name matches the query.
        best_score = min(best_score, 118)

    all_query_text = " ".join(sorted(direct_terms))
    best_score = max(
        best_score,
        partial_fuzzy_ratio(query, combined_text),
        token_overlap_score(all_query_text, combined_text),
    )

    for rule in get_ranking_rules(synonym_groups_signature()):
        if not (rule["query_terms"] & direct_terms):
            continue

        if has_search_phrase(name_text, rule["boost_name_terms"]):
            best_score = max(best_score, rule["boost_score"])
        elif has_search_phrase(name_text, rule["demote_name_terms"]):
            best_score = min(best_score, rule["demote_score"])

    return min(best_score, 125)


def search_parts(query, parts, minimum_score=58, limit=1000):
    """Return ranked parts whose score meets the minimum threshold."""

    scored_parts = []
    for part in parts:
        score = score_part(query, part)
        if score >= minimum_score:
            scored_parts.append((score, part))

    scored_parts.sort(key=lambda item: (-item[0], numeric_match_sort_key(query, item[1]), normalize_search_text(item[1].name)))
    return [part for _, part in scored_parts[:limit]]

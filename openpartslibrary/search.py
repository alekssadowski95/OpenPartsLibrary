import re
import unicodedata
from difflib import SequenceMatcher


SYNONYMS = {
    "alu": {"aluminium", "aluminum"},
    "aluminium": {"alu", "aluminum"},
    "aluminum": {"alu", "aluminium"},
    "bolt": {"screw", "fastener"},
    "fastener": {"bolt", "screw"},
    "guide": {"linear rail", "rail"},
    "guides": {"linear rail", "rail"},
    "hex": {"hexagon"},
    "hexagon": {"hex"},
    "linear guide": {"linear rail", "rail"},
    "nut": {"hex nut", "fastener"},
    "profile": {"extrusion", "rail"},
    "rail": {"profile", "extrusion"},
    "screw": {"bolt", "fastener"},
    "shim": {"spacer", "washer"},
    "spacer": {"shim", "washer"},
    "washer": {"shim", "spacer"},
}


def normalize_search_text(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.lower()
    value = re.sub(r"([a-z])(\d)", r"\1 \2", value)
    value = re.sub(r"(\d)([a-z])", r"\1 \2", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def expand_query_terms(query):
    normalized_query = normalize_search_text(query)
    direct_terms = {normalized_query} if normalized_query else set()
    synonym_terms = set()

    for token in normalized_query.split():
        direct_terms.add(token)
        synonym_terms.update(SYNONYMS.get(token, set()))

    return (
        {term for term in direct_terms if term},
        {term for term in synonym_terms if term and term not in direct_terms},
    )


def searchable_part_fields(part):
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


def fuzzy_ratio(query, text):
    query = normalize_search_text(query)
    text = normalize_search_text(text)
    if not query or not text:
        return 0

    return int(SequenceMatcher(None, query, text).ratio() * 100)


def partial_fuzzy_ratio(query, text):
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


def token_overlap_score(query, text):
    query_tokens = set(normalize_search_text(query).split())
    text_tokens = set(normalize_search_text(text).split())
    if not query_tokens or not text_tokens:
        return 0

    return int((len(query_tokens & text_tokens) / len(query_tokens)) * 100)


def is_numeric_term(term):
    return bool(re.fullmatch(r"\d+", normalize_search_text(term)))


def term_matches_text(term, text, threshold=88):
    term = normalize_search_text(term)
    text = normalize_search_text(text)
    if not term or not text:
        return False
    if term in text:
        return True

    return partial_fuzzy_ratio(term, text) >= threshold


def score_part(query, part):
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

    return min(best_score, 125)


def search_parts(query, parts, minimum_score=58, limit=1000):
    scored_parts = []
    for part in parts:
        score = score_part(query, part)
        if score >= minimum_score:
            scored_parts.append((score, part))

    scored_parts.sort(key=lambda item: (-item[0], normalize_search_text(item[1].name)))
    return [part for _, part in scored_parts[:limit]]

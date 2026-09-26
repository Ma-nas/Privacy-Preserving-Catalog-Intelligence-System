import re
from typing import Optional, List, Dict


def extract_keywords(text: str) -> List[str]:
    """Extracts distinctive keywords for tagging and indexing."""
    words = re.findall(r"\b[A-Za-z0-9\-]{3,}\b", text.lower())
    stop_words = {
        "and", "with", "the", "for", "from", "that", "this", "are", "have", "our",
        "you", "your", "all", "each", "both", "very", "more", "some", "item", "product",
    }
    keywords = [w for w in words if w not in stop_words and not w.isdigit()]
    # Return unique top keywords
    seen = set()
    result = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
        if len(result) >= 8:
            break
    return result


def generate_enriched_description(
    title: str,
    raw_desc: Optional[str] = None,
    category_path: Optional[str] = None,
) -> str:
    """
    Enriches catalog product descriptions with structured copywriting.
    Cleanly combines attributes, highlights key benefits, and optimizes for search.
    """
    clean_title = (title or "").strip()
    clean_desc = (raw_desc or "").strip()
    category = category_path or "General Merchandise"

    intro = f"Experience premium performance and refined craftsmanship with the {clean_title}."
    
    body = ""
    if clean_desc:
        body = f"\n\nHighlights & Specifications:\n{clean_desc}"
    
    footer = f"\n\nCategory: {category}\nDesigned for durability, effortless usability, and modern style."
    
    return f"{intro}{body}{footer}"

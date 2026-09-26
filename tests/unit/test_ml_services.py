import pytest
from ml_services.classification.model import CatalogClassifier
from ml_services.description.generator import generate_enriched_description, extract_keywords
from services.classifier_client import _stub_classify
from services.description_client import _stub_generate_description


def test_catalog_classifier_predictions():
    # Test Electronics classification
    cat, conf = CatalogClassifier.predict("Apple iPhone 15 Pro Max 256GB Titanium")
    assert "Electronics" in cat
    assert conf > 0.0

    # Test Fashion classification
    cat, conf = CatalogClassifier.predict("Men's Slim Fit Cotton T-Shirt")
    assert "Fashion" in cat
    assert conf > 0.0

    # Test Home & Kitchen classification
    cat, conf = CatalogClassifier.predict("Stainless Steel French Press Coffee Maker")
    assert "Home & Kitchen" in cat
    assert conf > 0.0


def test_catalog_classifier_empty_handling():
    cat, conf = CatalogClassifier.predict("")
    assert "General Merchandise" in cat
    assert conf >= 0.5


def test_keyword_extraction():
    sample_text = "Ultra durable waterproof running shoes with breathable mesh and rubber sole"
    keywords = extract_keywords(sample_text)
    assert "waterproof" in keywords
    assert "running" in keywords
    assert "shoes" in keywords
    # Ensure stop words are filtered out
    assert "and" not in keywords
    assert "with" not in keywords


def test_description_generator():
    desc = generate_enriched_description(
        title="Ergonomic Mechanical Keyboard",
        raw_desc="RGB backlit with hot-swappable tactile switches",
        category_path="Electronics > Computer Accessories",
    )
    assert "Ergonomic Mechanical Keyboard" in desc
    assert "RGB backlit" in desc
    assert "Electronics > Computer Accessories" in desc


def test_stub_fallbacks():
    stub_res = _stub_classify("Sony Bluetooth noise canceling wireless headphones")
    assert "Electronics" in stub_res.path
    assert stub_res.confidence > 0.8

    stub_desc = _stub_generate_description("Yoga Mat", "5mm thick", "Sports")
    assert "Yoga Mat" in stub_desc

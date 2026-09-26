import pytest
import uuid
from pydantic import ValidationError
from api.schemas import CatalogItemCreate, CatalogItemBatchIngest, CatalogItemResponse


def test_catalog_item_create_valid():
    item = CatalogItemCreate(
        sku="SKU-12345",
        raw_title="Smart Watch Series 9",
        raw_description="Fitness tracker with OLED screen",
    )
    assert item.sku == "SKU-12345"
    assert item.raw_title == "Smart Watch Series 9"


def test_catalog_item_create_missing_required():
    with pytest.raises(ValidationError):
        CatalogItemCreate(sku="SKU-ONLY")


def test_batch_ingest_empty_disallowed():
    with pytest.raises(ValidationError):
        CatalogItemBatchIngest(items=[])


def test_batch_ingest_valid():
    batch = CatalogItemBatchIngest(
        items=[
            CatalogItemCreate(sku="SKU-A", raw_title="Title A"),
            CatalogItemCreate(sku="SKU-B", raw_title="Title B"),
        ]
    )
    assert len(batch.items) == 2

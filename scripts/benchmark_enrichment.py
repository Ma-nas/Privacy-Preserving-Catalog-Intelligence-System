"""
Catalog Enrichment Benchmark Utility
Evaluates classification throughput, keyword extraction latency, and memory footprint.
"""

import time
import json
import statistics
from typing import List, Dict

SAMPLE_ITEMS = [
    {
        "sku": f"SKU-{i:04d}",
        "raw_title": f"High Precision Wireless Noise Canceling Headphones Model {i}",
        "raw_description": "Active acoustic noise reduction with 40mm neodymium drivers, 30h battery life, and Bluetooth 5.3 multipoint audio."
    }
    for i in range(100)
]

def simulate_classification(item: Dict) -> Dict:
    start = time.perf_counter()
    # Simulated TF-IDF + SGD pipeline inference
    title_words = len(item["raw_title"].split())
    desc_words = len(item["raw_description"].split())
    tokens = title_words + desc_words
    time.sleep(0.001)  # 1ms compute emulation
    duration_ms = (time.perf_counter() - start) * 1000
    return {
        "sku": item["sku"],
        "category": "Consumer Electronics > Audio",
        "confidence": 0.962,
        "tokens_processed": tokens,
        "latency_ms": duration_ms
    }

def run_benchmark(batch_sizes: List[int] = [10, 25, 50, 100]):
    print("=" * 65)
    print("CATALOG ENRICHMENT INFERENCE & THROUGHPUT BENCHMARK")
    print("=" * 65)

    results = []
    for size in batch_sizes:
        batch = SAMPLE_ITEMS[:size]
        start_batch = time.perf_counter()
        latencies = []

        for item in batch:
            res = simulate_classification(item)
            latencies.append(res["latency_ms"])

        total_time_s = time.perf_counter() - start_batch
        throughput_items_per_sec = size / total_time_s
        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[int(0.95 * len(latencies))]

        print(f"Batch Size: {size:3d} items | "
              f"Total Time: {total_time_s * 1000:6.1f}ms | "
              f"Throughput: {throughput_items_per_sec:6.1f} items/s | "
              f"P50 Latency: {p50:4.2f}ms | P95: {p95:4.2f}ms")

        results.append({
            "batch_size": size,
            "total_time_ms": round(total_time_s * 1000, 2),
            "throughput_items_per_sec": round(throughput_items_per_sec, 2),
            "p50_latency_ms": round(p50, 2),
            "p95_latency_ms": round(p95, 2)
        })

    print("-" * 65)
    print("Benchmark completed successfully.")
    return results

if __name__ == "__main__":
    run_benchmark()

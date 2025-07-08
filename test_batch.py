"""
Test script for NL2Pinecone Query Agent using batch processing endpoint

This script loads test samples and processes them through the /batch-query endpoint,
then compares results with expected filters where available.
"""

import requests
import json
import time
from typing import Dict, List, Any
from test_samples import ALL_SAMPLES, ALL_QUERIES, PRIMARY_SAMPLES

# Configuration
API_BASE_URL = "http://localhost:8000"
BATCH_QUERY_ENDPOINT = f"{API_BASE_URL}/batch-query"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"


def check_api_health() -> bool:
    """Check if the API is running and healthy."""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        return response.status_code == 200 and response.json().get("status") == "healthy"
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def process_batch_queries(queries: List[str]) -> Dict[str, Any]:
    """Process queries using the batch endpoint."""
    try:
        response = requests.post(
            BATCH_QUERY_ENDPOINT,
            json=queries,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Batch processing failed: {e}")
        return {"error": str(e)}


def compare_filters(expected: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
    """Compare expected and actual filters, returning comparison results."""
    comparison = {
        "exact_match": expected == actual,
        "missing_fields": [],
        "extra_fields": [],
        "field_mismatches": []
    }
    
    # Check for missing fields
    for key in expected:
        if key not in actual:
            comparison["missing_fields"].append(key)
        elif expected[key] != actual[key]:
            comparison["field_mismatches"].append({
                "field": key,
                "expected": expected[key],
                "actual": actual[key]
            })
    
    # Check for extra fields
    for key in actual:
        if key not in expected:
            comparison["extra_fields"].append(key)
    
    return comparison


def run_batch_test():
    """Run comprehensive batch test."""
    print("🚀 Starting NL2Pinecone Agent Batch Test")
    print("=" * 50)
    
    # Check API health
    print("1. Checking API health...")
    if not check_api_health():
        print("❌ API is not healthy. Please start the FastAPI server first:")
        print("   uv run app.py")
        return
    print("✅ API is healthy")
    
    # Process all queries in batch
    print(f"\n2. Processing {len(ALL_QUERIES)} queries in batch...")
    start_time = time.time()
    
    batch_result = process_batch_queries(ALL_QUERIES)
    
    if "error" in batch_result:
        print(f"❌ Batch processing failed: {batch_result['error']}")
        return
    
    processing_time = time.time() - start_time
    total_processed = batch_result.get("total_processed", 0)
    
    print(f"✅ Processed {total_processed} queries in {processing_time:.2f} seconds")
    print(f"⚡ Average: {processing_time/total_processed:.3f} seconds per query")
    
    # Analyze results
    print(f"\n3. Analyzing results...")
    results = batch_result.get("results", [])
    
    if len(results) != len(ALL_SAMPLES):
        print(f"⚠️  Warning: Expected {len(ALL_SAMPLES)} results, got {len(results)}")
    
    # Compare with expected results for samples that have them
    exact_matches = 0
    partial_matches = 0
    mismatches = 0
    
    print(f"\n4. Detailed Results Analysis")
    print("-" * 50)
    
    for i, result in enumerate(results):
        if i >= len(ALL_SAMPLES):
            break
            
        sample = ALL_SAMPLES[i]
        query = result.get("original_query", "")
        actual_filter = result.get("pinecone_filter", {})
        expected_filter = sample.get("expected_filter", {})
        
        print(f"\n[{i+1}] Query: {query}")
        print(f"    Generated: {json.dumps(actual_filter, indent=15)}")
        
        if expected_filter:
            comparison = compare_filters(expected_filter, actual_filter)
            
            if comparison["exact_match"]:
                print("    ✅ EXACT MATCH")
                exact_matches += 1
            elif not comparison["missing_fields"] and not comparison["field_mismatches"]:
                print("    🟡 PARTIAL MATCH (extra fields)")
                partial_matches += 1
            else:
                print("    ❌ MISMATCH")
                if comparison["missing_fields"]:
                    print(f"       Missing: {comparison['missing_fields']}")
                if comparison["field_mismatches"]:
                    print(f"       Incorrect: {[m['field'] for m in comparison['field_mismatches']]}")
                mismatches += 1
                
            print(f"    Expected:  {json.dumps(expected_filter, indent=15)}")
        else:
            print("    📝 NO EXPECTED RESULT (manual review needed)")
    
    # Summary
    print(f"\n5. Summary")
    print("=" * 50)
    print(f"Total queries processed: {total_processed}")
    print(f"Processing time: {processing_time:.2f} seconds")
    print(f"Average time per query: {processing_time/total_processed:.3f} seconds")
    
    samples_with_expected = len([s for s in ALL_SAMPLES if "expected_filter" in s])
    if samples_with_expected > 0:
        print(f"\nAccuracy (samples with expected results):")
        print(f"  ✅ Exact matches: {exact_matches}/{samples_with_expected} ({exact_matches/samples_with_expected*100:.1f}%)")
        print(f"  🟡 Partial matches: {partial_matches}/{samples_with_expected} ({partial_matches/samples_with_expected*100:.1f}%)")
        print(f"  ❌ Mismatches: {mismatches}/{samples_with_expected} ({mismatches/samples_with_expected*100:.1f}%)")
        
        success_rate = (exact_matches + partial_matches) / samples_with_expected * 100
        print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
    
    # Save results to file
    output_file = "batch_test_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "test_info": {
                "total_queries": len(ALL_QUERIES),
                "processing_time": processing_time,
                "avg_time_per_query": processing_time/total_processed,
                "exact_matches": exact_matches,
                "partial_matches": partial_matches,
                "mismatches": mismatches,
                "samples_with_expected": samples_with_expected
            },
            "batch_result": batch_result,
            "samples": ALL_SAMPLES
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {output_file}")
    print("\n🎉 Batch test completed!")


def run_primary_samples_test():
    """Run test only on primary samples from project requirements."""
    print("🎯 Testing Primary Samples (Project Requirements)")
    print("=" * 50)
    
    if not check_api_health():
        print("❌ API is not healthy. Please start the FastAPI server first.")
        return
    
    primary_queries = [sample["query"] for sample in PRIMARY_SAMPLES]
    batch_result = process_batch_queries(primary_queries)
    
    if "error" in batch_result:
        print(f"❌ Batch processing failed: {batch_result['error']}")
        return
    
    results = batch_result.get("results", [])
    
    print(f"Processing {len(PRIMARY_SAMPLES)} primary test cases...")
    all_passed = True
    
    for i, (sample, result) in enumerate(zip(PRIMARY_SAMPLES, results)):
        query = sample["query"]
        expected = sample["expected_filter"]
        actual = result.get("pinecone_filter", {})
        
        print(f"\n[{i+1}] {query}")
        comparison = compare_filters(expected, actual)
        
        if comparison["exact_match"]:
            print("✅ PASS")
        else:
            print("❌ FAIL")
            print(f"  Expected: {expected}")
            print(f"  Got:      {actual}")
            all_passed = False
    
    print(f"\n{'✅ ALL PRIMARY TESTS PASSED!' if all_passed else '❌ Some tests failed'}")
    return all_passed


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--primary":
        run_primary_samples_test()
    else:
        run_batch_test()

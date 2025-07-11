"""
Test script for NL2Pinecone Query Agent using batch processing endpoint

This script loads test samples from test_samples-queries.json and processes them 
through the /batch-query endpoint, then compares results with expected filters.
"""

import requests
import json
import time
from typing import Dict, List, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
BATCH_QUERY_ENDPOINT = f"{API_BASE_URL}/batch-query"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
TEST_SAMPLES_FILE = "test_samples-queries.json"


def load_test_samples() -> Dict[str, Any]:
    """Load test samples from JSON file."""
    try:
        with open(TEST_SAMPLES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Test samples file not found: {TEST_SAMPLES_FILE}")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing test samples file: {e}")
        return {}


def get_all_samples(test_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get all samples from test data."""
    all_samples = []
    for category in ["primary_samples", "additional_samples", "edge_case_samples"]:
        all_samples.extend(test_data.get(category, []))
    return all_samples


def get_all_queries(test_data: Dict[str, Any]) -> List[str]:
    """Get all queries from test data."""
    all_samples = get_all_samples(test_data)
    return [sample["query"] for sample in all_samples]


def get_primary_samples(test_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get primary samples from test data."""
    return test_data.get("primary_samples", [])


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
        "field_mismatches": [],
        "extra_fields": []
    }
    
    # Check for missing fields in actual
    for key, value in expected.items():
        if key not in actual:
            comparison["missing_fields"].append(key)
        elif actual[key] != value:
            comparison["field_mismatches"].append({
                "field": key,
                "expected": value,
                "actual": actual[key]
            })
    
    # Check for extra fields in actual
    for key in actual:
        if key not in expected:
            comparison["extra_fields"].append(key)
    
    return comparison


def run_batch_test():
    """Run batch test on all samples."""
    print("🧪 NL2Pinecone Query Agent - Batch Test")
    print("=" * 50)
    
    # Load test samples
    print("1. Loading test samples...")
    test_data = load_test_samples()
    if not test_data:
        print("❌ Failed to load test samples. Exiting.")
        return
    
    all_samples = get_all_samples(test_data)
    all_queries = get_all_queries(test_data)
    
    print(f"   📊 Loaded {len(all_samples)} test samples")
    print(f"   📋 Primary: {len(test_data.get('primary_samples', []))}")
    print(f"   📋 Additional: {len(test_data.get('additional_samples', []))}")
    print(f"   📋 Edge cases: {len(test_data.get('edge_case_samples', []))}")
    
    if not check_api_health():
        print("❌ API is not healthy. Please start the FastAPI server first.")
        return
    
    print(f"\n2. Processing {len(all_queries)} queries in batch...")
    start_time = time.time()
    
    batch_result = process_batch_queries(all_queries)
    
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
    
    if len(results) != len(all_samples):
        print(f"⚠️  Warning: Expected {len(all_samples)} results, got {len(results)}")
    
    # Compare with expected results for samples that have them
    exact_matches = 0
    partial_matches = 0
    mismatches = 0
    
    print(f"\n4. Detailed Results Analysis")
    print("-" * 50)
    
    for i, result in enumerate(results):
        if i >= len(all_samples):
            break
            
        sample = all_samples[i]
        query = result.get("original_query", "")
        actual_filter = result.get("pinecone_filter", {})
        expected_filter = sample.get("expected_results", {})
        
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
    
    samples_with_expected = len([s for s in all_samples if "expected_results" in s])
    if samples_with_expected > 0:
        print(f"\nAccuracy (samples with expected results):")
        print(f"  ✅ Exact matches: {exact_matches}/{samples_with_expected} ({exact_matches/samples_with_expected*100:.1f}%)")
        print(f"  🟡 Partial matches: {partial_matches}/{samples_with_expected} ({partial_matches/samples_with_expected*100:.1f}%)")
        print(f"  ❌ Mismatches: {mismatches}/{samples_with_expected} ({mismatches/samples_with_expected*100:.1f}%)")
        
        success_rate = (exact_matches + partial_matches) / samples_with_expected * 100
        print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
    
    # Save results to file
    output_file = "batch_query_test-results.json"
    with open(output_file, "w") as f:
        json.dump({
            "test_info": {
                "total_queries": len(all_queries),
                "processing_time": processing_time,
                "avg_time_per_query": processing_time/total_processed,
                "exact_matches": exact_matches,
                "partial_matches": partial_matches,
                "mismatches": mismatches,
                "samples_with_expected": samples_with_expected
            },
            "batch_result": batch_result,
            "samples": all_samples
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {output_file}")
    print("\n🎉 Batch test completed!")


def run_primary_samples_test():
    """Run test only on primary samples from project requirements."""
    print("🎯 Testing Primary Samples (Project Requirements)")
    print("=" * 50)
    
    # Load test samples
    test_data = load_test_samples()
    if not test_data:
        print("❌ Failed to load test samples. Exiting.")
        return
    
    if not check_api_health():
        print("❌ API is not healthy. Please start the FastAPI server first.")
        return
    
    primary_samples = get_primary_samples(test_data)
    primary_queries = [sample["query"] for sample in primary_samples]
    batch_result = process_batch_queries(primary_queries)
    
    if "error" in batch_result:
        print(f"❌ Batch processing failed: {batch_result['error']}")
        return
    
    results = batch_result.get("results", [])
    
    print(f"Processing {len(primary_samples)} primary test cases...")
    all_passed = True
    
    for i, (sample, result) in enumerate(zip(primary_samples, results)):
        query = sample["query"]
        expected = sample["expected_results"]
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

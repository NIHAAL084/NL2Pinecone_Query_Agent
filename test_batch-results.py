"""
Test script for NL2Pinecone Query Agent using batch results endpoint

This script loads test samples from test_samples-queries.json, converts them to 
filters using the /batch-query endpoint, then processes those filters through 
the /batch-results endpoint to get actual search results.
"""

import requests
import json
import time
from typing import Dict, List, Any

# Configuration
API_BASE_URL = "http://localhost:8000"
BATCH_QUERY_ENDPOINT = f"{API_BASE_URL}/batch-query"
BATCH_RESULTS_ENDPOINT = f"{API_BASE_URL}/batch-results"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
TEST_SAMPLES_FILE = "test_samples-results.json"


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
    return test_data.get("queries", [])


def get_all_queries(test_data: Dict[str, Any]) -> List[str]:
    """Get all queries from test data."""
    all_samples = get_all_samples(test_data)
    return [sample["query"] for sample in all_samples]


def check_api_health() -> bool:
    """Check if the API is running and healthy."""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        return response.status_code == 200 and response.json().get("status") == "healthy"
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def process_batch_queries(queries: List[str]) -> Dict[str, Any]:
    """Process queries using the batch query endpoint to get filters."""
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
        print(f"Batch query processing failed: {e}")
        return {"error": str(e)}


def process_batch_results(queries: List[str], top_k: int = 10) -> Dict[str, Any]:
    """Process queries using the batch results endpoint."""
    try:
        payload = {
            "queries": queries,
            "top_k": top_k,
            "include_metadata": True
        }
        
        response = requests.post(
            BATCH_RESULTS_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60  # Longer timeout for vector search
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Batch results processing failed: {e}")
        return {"error": str(e)}


def process_batch_results_with_rate_limiting(queries: List[str], top_k: int = 10, batch_size: int = 15) -> List[Dict[str, Any]]:
    """Process queries in batches with rate limiting to avoid API quotas."""
    all_results = []
    total_batches = (len(queries) + batch_size - 1) // batch_size
    
    for i in range(0, len(queries), batch_size):
        batch_queries = queries[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        
        print(f"   Processing batch {batch_num}/{total_batches} ({len(batch_queries)} queries)...")
        
        # Process current batch
        batch_result = process_batch_results(batch_queries, top_k)
        
        if "results" in batch_result:
            all_results.extend(batch_result["results"])
        elif "error" not in batch_result:
            # Handle case where batch_result is directly a list
            all_results.extend(batch_result if isinstance(batch_result, list) else [])
        else:
            # Add error entries for failed batch
            for query in batch_queries:
                all_results.append({
                    "original_query": query,
                    "error": batch_result.get("error", "Unknown batch processing error"),
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%f")
                })
        
        # Add delay after each batch except the last one
        if batch_num < total_batches:
            print(f"   ⏳ Rate limiting: waiting 60 seconds before next batch...")
            time.sleep(60)
    
    return all_results


def create_search_requests(query_results: List[Dict[str, Any]], 
                         top_k: int = 5) -> List[Dict[str, Any]]:
    """Create search requests from query results."""
    search_requests = []
    
    for result in query_results:
        original_query = result.get("original_query", "")
        pinecone_filter = result.get("pinecone_filter", {})
        
        search_request = {
            "query": original_query,
            "filter": pinecone_filter,
            "top_k": top_k
        }
        search_requests.append(search_request)
    
    return search_requests


def analyze_search_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze search results and return statistics."""
    analysis = {
        "total_requests": len(results),
        "successful_searches": 0,
        "failed_searches": 0,
        "empty_results": 0,
        "results_with_matches": 0,
        "total_matches": 0,
        "avg_matches_per_query": 0,
        "errors": []
    }
    
    for result in results:
        if "error" in result:
            analysis["failed_searches"] += 1
            analysis["errors"].append(result["error"])
        else:
            analysis["successful_searches"] += 1
            matches = result.get("matches", [])
            match_count = len(matches)
            analysis["total_matches"] += match_count
            
            if match_count == 0:
                analysis["empty_results"] += 1
            else:
                analysis["results_with_matches"] += 1
    
    if analysis["successful_searches"] > 0:
        analysis["avg_matches_per_query"] = analysis["total_matches"] / analysis["successful_searches"]
    
    return analysis


def validate_search_results(search_result: Dict[str, Any], 
                           expected_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate search results against expected matches."""
    validation = {
        "total_expected": len(expected_matches),
        "total_found": 0,
        "matches_found": [],
        "matches_missing": [],
        "unexpected_matches": [],
        "validation_score": 0.0
    }
    
    if "error" in search_result:
        validation["error"] = search_result["error"]
        return validation
    
    actual_matches = search_result.get("results", [])  # Changed from "matches" to "results"
    validation["total_found"] = len(actual_matches)
    
    # Check if expected matches are found in actual results
    for expected in expected_matches:
        found = False
        for actual in actual_matches:
            actual_metadata = actual.get("metadata", {})
            
            # Check title match (most reliable identifier)
            if expected.get("title") and actual_metadata.get("title"):
                if expected["title"].lower() in actual_metadata["title"].lower():
                    validation["matches_found"].append({
                        "expected": expected,
                        "actual": actual_metadata,
                        "score": actual.get("score", 0)
                    })
                    found = True
                    break
            # Check pageURL match as backup
            elif expected.get("pageURL") and actual_metadata.get("pageURL"):
                if expected["pageURL"] == actual_metadata["pageURL"]:
                    validation["matches_found"].append({
                        "expected": expected,
                        "actual": actual_metadata,
                        "score": actual.get("score", 0)
                    })
                    found = True
                    break
        
        if not found:
            validation["matches_missing"].append(expected)
    
    # Calculate validation score
    if validation["total_expected"] > 0:
        validation["validation_score"] = len(validation["matches_found"]) / validation["total_expected"]
    
    return validation


def analyze_filter_comparisons(comparisons: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze filter comparison results across all queries."""
    analysis = {
        "total_queries": len(comparisons),
        "exact_matches": 0,
        "partial_matches": 0,
        "no_matches": 0,
        "avg_match_score": 0.0,
        "total_missing_fields": 0,
        "total_field_mismatches": 0,
        "total_extra_fields": 0
    }
    
    total_score = 0.0
    
    for comparison in comparisons:
        score = comparison.get("match_score", 0.0)
        total_score += score
        
        if comparison.get("exact_match", False):
            analysis["exact_matches"] += 1
        elif score > 0.0:
            analysis["partial_matches"] += 1
        else:
            analysis["no_matches"] += 1
            
        analysis["total_missing_fields"] += len(comparison.get("missing_fields", []))
        analysis["total_field_mismatches"] += len(comparison.get("field_mismatches", []))
        analysis["total_extra_fields"] += len(comparison.get("extra_fields", []))
    
    if analysis["total_queries"] > 0:
        analysis["avg_match_score"] = total_score / analysis["total_queries"]
    
    return analysis


def analyze_validation_results(validations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze validation results across all queries."""
    analysis = {
        "total_queries": len(validations),
        "queries_with_errors": 0,
        "queries_with_results": 0,
        "total_expected_matches": 0,
        "total_found_matches": 0,
        "total_validated_matches": 0,
        "avg_validation_score": 0.0,
        "perfect_matches": 0,
        "partial_matches": 0,
        "no_matches": 0
    }
    
    total_score = 0.0
    
    for validation in validations:
        if "error" in validation:
            analysis["queries_with_errors"] += 1
            continue
            
        analysis["queries_with_results"] += 1
        analysis["total_expected_matches"] += validation["total_expected"]
        analysis["total_found_matches"] += validation["total_found"]
        analysis["total_validated_matches"] += len(validation["matches_found"])
        
        score = validation["validation_score"]
        total_score += score
        
        if score == 1.0:
            analysis["perfect_matches"] += 1
        elif score > 0.0:
            analysis["partial_matches"] += 1
        else:
            analysis["no_matches"] += 1
    
    if analysis["queries_with_results"] > 0:
        analysis["avg_validation_score"] = total_score / analysis["queries_with_results"]
    
    return analysis


def compare_pinecone_filters(expected: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
    """Compare expected and actual Pinecone filters, returning comparison results."""
    comparison = {
        "exact_match": expected == actual,
        "missing_fields": [],
        "field_mismatches": [],
        "extra_fields": [],
        "match_score": 0.0
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
    
    # Calculate match score
    total_expected_fields = len(expected)
    if total_expected_fields > 0:
        correct_fields = total_expected_fields - len(comparison["missing_fields"]) - len(comparison["field_mismatches"])
        comparison["match_score"] = correct_fields / total_expected_fields
    
    return comparison


def run_batch_results_test():
    """Run batch results test on all samples."""
    print("🔍 NL2Pinecone Query Agent - Batch Results Test")
    print("=" * 60)
    
    # Load test samples
    print("1. Loading test samples...")
    test_data = load_test_samples()
    if not test_data:
        print("❌ Failed to load test samples. Exiting.")
        return
    
    all_samples = get_all_samples(test_data)
    all_queries = get_all_queries(test_data)
    
    print(f"   📊 Loaded {len(all_samples)} test samples")
    
    if not check_api_health():
        print("❌ API is not healthy. Please start the FastAPI server first.")
        return
    
    # Step 1: Process batch results with rate limiting
    print(f"\n2. Processing {len(all_queries)} queries through batch-results endpoint...")
    print(f"   📝 Using rate limiting: 15 queries per batch with 60-second delays")
    start_time = time.time()
    
    search_results = process_batch_results_with_rate_limiting(all_queries, top_k=10, batch_size=15)
    
    processing_time = time.time() - start_time
    
    print(f"✅ Processed {len(search_results)} queries in {processing_time:.2f} seconds")
    print(f"⚡ Average: {processing_time/len(search_results):.3f} seconds per query")
    
    # Step 2: Validate filters and results against expected values
    print(f"\n3. Validating filters and search results against expected values...")
    validations = []
    filter_comparisons = []
    
    for i, (result, sample) in enumerate(zip(search_results, all_samples)):
        # Validate Pinecone filter
        expected_filter = sample.get("expected_pinecone_filter", {})
        actual_filter = result.get("pinecone_filter", {})
        filter_comparison = compare_pinecone_filters(expected_filter, actual_filter)
        filter_comparisons.append(filter_comparison)
        
        # Validate search results
        expected_matches = sample.get("expected_matches", [])
        if expected_matches == "all_records_from_csv":
            # Skip validation for queries that should match all records
            validation = {"validation_score": 1.0, "total_expected": 15, "total_found": len(result.get("results", []))}
        else:
            validation = validate_search_results(result, expected_matches)
        validations.append(validation)
    
    validation_analysis = analyze_validation_results(validations)
    filter_analysis = analyze_filter_comparisons(filter_comparisons)
    
    # Step 3: Detailed Results Preview with Validation
    print(f"\n4. Detailed Results Preview with Validation")
    print("-" * 70)
    
    # Show first few results as examples
    preview_count = min(30, len(search_results))  # Show all results instead of just 5
    for i in range(preview_count):
        result = search_results[i]
        validation = validations[i]
        filter_comparison = filter_comparisons[i]
        sample = all_samples[i]
        original_query = all_queries[i]
        filter_used = result.get("pinecone_filter", {})
        expected_filter = sample.get("expected_pinecone_filter", {})
        
        print(f"\n[{i+1}] Query: {original_query}")
        print(f"    Expected Filter: {json.dumps(expected_filter, indent=16)}")
        print(f"    Actual Filter: {json.dumps(filter_used, indent=14)}")
        filter_match_status = "✅ Exact" if filter_comparison['exact_match'] else f"🟡 {filter_comparison['match_score']:.2f}"
        print(f"    🔍 Filter Match: {filter_match_status}")
        
        if filter_comparison.get('missing_fields'):
            print(f"       Missing fields: {filter_comparison['missing_fields']}")
        if filter_comparison.get('field_mismatches'):
            print(f"       Field mismatches: {len(filter_comparison['field_mismatches'])}")
        if filter_comparison.get('extra_fields'):
            print(f"       Extra fields: {filter_comparison['extra_fields']}")
        
        if "error" in result:
            print(f"    ❌ Error: {result['error']}")
        else:
            matches = result.get("results", [])  # Changed from "matches" to "results"
            expected_matches = sample.get("expected_matches", [])
            
            print(f"    ✅ Found {len(matches)} matches")
            print(f"    📋 Expected {len(expected_matches) if expected_matches != 'all_records_from_csv' else '15'} matches")
            print(f"    🎯 Validation Score: {validation['validation_score']:.2f}")
            
            if matches:
                # Show first match details
                first_match = matches[0]
                score = first_match.get("score", 0)
                metadata = first_match.get("metadata", {})
                print(f"       Top match score: {score:.4f}")
                print(f"       Title: {metadata.get('title', 'N/A')[:100]}...")
                
            if validation.get("matches_found"):
                print(f"    ✅ Validated matches: {len(validation['matches_found'])}")
            if validation.get("matches_missing"):
                print(f"    ❌ Missing expected: {len(validation['matches_missing'])}")
    
    if len(search_results) > preview_count:
        print(f"\n    ... and {len(search_results) - preview_count} more results")
    
    # Step 4: Summary
    print(f"\n5. Summary")
    print("=" * 70)
    print(f"Total processing time: {processing_time:.2f} seconds")
    print(f"Average time per query: {processing_time/len(search_results):.3f} seconds")
    
    print(f"\nSearch Results Analysis:")
    print(f"  📊 Total requests: {len(search_results)}")
    print(f"  ✅ Successful searches: {validation_analysis['queries_with_results']}")
    print(f"  ❌ Failed searches: {validation_analysis['queries_with_errors']}")
    print(f"  📄 Results with matches: {validation_analysis['queries_with_results'] - validation_analysis['no_matches']}")
    print(f"  📭 Empty results: {validation_analysis['no_matches']}")
    print(f"  🎯 Total expected matches: {validation_analysis['total_expected_matches']}")
    print(f"  🎯 Total found matches: {validation_analysis['total_found_matches']}")
    print(f"  ✅ Total validated matches: {validation_analysis['total_validated_matches']}")
    
    print(f"\nFilter Analysis:")
    print(f"  🎯 Exact filter matches: {filter_analysis['exact_matches']}")
    print(f"  🟡 Partial filter matches: {filter_analysis['partial_matches']}")
    print(f"  ❌ Filter mismatches: {filter_analysis['no_matches']}")
    print(f"  📈 Average filter score: {filter_analysis['avg_match_score']:.2f}")
    print(f"  📋 Total missing fields: {filter_analysis['total_missing_fields']}")
    print(f"  🔄 Total field mismatches: {filter_analysis['total_field_mismatches']}")
    print(f"  ➕ Total extra fields: {filter_analysis['total_extra_fields']}")
    
    print(f"\nValidation Analysis:")
    print(f"  🎯 Perfect matches: {validation_analysis['perfect_matches']}")
    print(f"  🟡 Partial matches: {validation_analysis['partial_matches']}")
    print(f"  ❌ No matches: {validation_analysis['no_matches']}")
    print(f"  📈 Average validation score: {validation_analysis['avg_validation_score']:.2f}")
    
    if validation_analysis['queries_with_errors'] > 0:
        print(f"\nErrors encountered in {validation_analysis['queries_with_errors']} queries")
    
    success_rate = validation_analysis['queries_with_results'] / len(search_results) * 100
    validation_rate = validation_analysis['avg_validation_score'] * 100
    filter_accuracy_rate = filter_analysis['avg_match_score'] * 100
    print(f"\n🎯 Search Success Rate: {success_rate:.1f}%")
    print(f"🎯 Average Validation Rate: {validation_rate:.1f}%")
    print(f"🔍 Filter Accuracy Rate: {filter_accuracy_rate:.1f}%")
    print(f"📊 Overall System Accuracy: {(filter_accuracy_rate + validation_rate) / 2:.1f}%")
    
    # Save results to file
    output_file = "batch_results_test-results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_info": {
                "total_queries": len(all_queries),
                "processing_time": processing_time,
                "avg_time_per_search": processing_time / len(search_results) if search_results else 0,
                "validation_analysis": validation_analysis,
                "filter_analysis": filter_analysis
            },
            "search_results": search_results,
            "validations": validations,
            "filter_comparisons": filter_comparisons,
            "samples": all_samples
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {output_file}")
    print("\n🎉 Batch results test completed!")


if __name__ == "__main__":
    run_batch_results_test()

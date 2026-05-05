"""
Mini Benchmark Runner

Runs SAFE, non-NSFW text benchmarks on LLM models.
All prompts are neutral and non-sexual.
"""
import requests
import time
from typing import List, Dict, Any, Optional
from config import get_settings

settings = get_settings()


# =============================================
# SAFE BENCHMARK PROMPTS - NO NSFW CONTENT
# =============================================

BENCHMARK_PROMPTS = {
    "instruction_en": {
        "type": "instruction",
        "language": "en",
        "prompt": "Explain the steps to organize a project folder clearly. List at least 5 steps in a numbered format.",
        "expected_format": "numbered_list",
        "min_items": 5,
    },
    "instruction_id": {
        "type": "instruction",
        "language": "id",
        "prompt": "Jelaskan langkah-langkah untuk mengatur folder proyek dengan rapi. Berikan minimal 5 langkah dalam format bernomor.",
        "expected_format": "numbered_list",
        "min_items": 5,
    },
    "formatting": {
        "type": "formatting",
        "language": "en",
        "prompt": "Create a markdown table comparing 3 popular programming languages (Python, JavaScript, Rust) across these dimensions: typing system, primary use case, and learning curve.",
        "expected_format": "markdown_table",
        "min_rows": 3,
    },
    "verbosity_short": {
        "type": "verbosity",
        "language": "en",
        "prompt": "In exactly one sentence, explain what an API is.",
        "expected_format": "single_sentence",
        "max_sentences": 1,
    },
    "verbosity_detailed": {
        "type": "verbosity",
        "language": "en",
        "prompt": "Write a detailed 3-paragraph explanation of how REST APIs work, including examples of HTTP methods.",
        "expected_format": "paragraphs",
        "min_paragraphs": 3,
    },
    "coding": {
        "type": "coding",
        "language": "en",
        "prompt": "Write a Python function called 'calculate_average' that takes a list of numbers and returns their average. Include a docstring and handle the empty list case.",
        "expected_format": "code_block",
        "required_elements": ["def calculate_average", "docstring", "if", "return"],
    },
}


def run_benchmark_sync(
    model_id: str,
    benchmark_type: str,
    timeout: float = 60.0
) -> Dict[str, Any]:
    """
    Run a single benchmark on a model (synchronous version using requests).
    
    Args:
        model_id: The OpenRouter model ID.
        benchmark_type: Type of benchmark to run.
        timeout: Request timeout in seconds.
        
    Returns:
        Benchmark result dictionary.
    """
    if benchmark_type not in BENCHMARK_PROMPTS:
        return {
            "model_id": model_id,
            "benchmark_type": benchmark_type,
            "status": "error",
            "error": f"Unknown benchmark type: {benchmark_type}"
        }
    
    benchmark = BENCHMARK_PROMPTS[benchmark_type]
    prompt = benchmark["prompt"]
    
    # Call OpenRouter API
    url = f"{settings.openrouter_base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://smartmove.local",
        "X-Title": "SmartMove Benchmark"
    }
    
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.3,  # Lower temperature for consistent benchmarking
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        latency_ms = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            
            # Evaluate the response
            score, status, notes = evaluate_response(content, benchmark)
            
            return {
                "model_id": model_id,
                "benchmark_type": benchmark_type,
                "prompt": prompt,
                "response": content[:2000],  # Truncate long responses
                "latency_ms": round(latency_ms, 2),
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "status": status,
                "score": score,
                "notes": notes,
            }
        elif response.status_code == 429:
            return {
                "model_id": model_id,
                "benchmark_type": benchmark_type,
                "status": "rate_limited",
                "error": "Rate limited by API"
            }
        else:
            error_text = response.text[:500]
            
            # Check for content policy refusal
            if "content policy" in error_text.lower() or "refused" in error_text.lower():
                return {
                    "model_id": model_id,
                    "benchmark_type": benchmark_type,
                    "status": "refusal",
                    "error": "Model refused to respond"
                }
            
            return {
                "model_id": model_id,
                "benchmark_type": benchmark_type,
                "status": "error",
                "error": f"API error {response.status_code}: {error_text}"
            }
            
    except requests.exceptions.Timeout:
        return {
            "model_id": model_id,
            "benchmark_type": benchmark_type,
            "status": "timeout",
            "latency_ms": timeout * 1000,
            "error": "Request timed out"
        }
    except Exception as e:
        return {
            "model_id": model_id,
            "benchmark_type": benchmark_type,
            "status": "error",
            "error": str(e)
        }


# Keep async wrapper for compatibility with existing code
async def run_benchmark(
    model_id: str,
    benchmark_type: str,
    timeout: float = 60.0
) -> Dict[str, Any]:
    """
    Async wrapper around run_benchmark_sync for compatibility.
    Uses synchronous requests library under the hood (works better on Windows).
    """
    return run_benchmark_sync(model_id, benchmark_type, timeout)


def evaluate_response(content: str, benchmark: Dict[str, Any]) -> tuple:
    """
    Evaluate a model's response against benchmark criteria.
    
    Args:
        content: The model's response.
        benchmark: The benchmark configuration.
        
    Returns:
        Tuple of (score, status, notes).
    """
    if not content or len(content.strip()) < 10:
        return 0.0, "partial", "Response too short or empty"
    
    expected_format = benchmark.get("expected_format")
    score = 0.0
    notes = []
    
    if expected_format == "numbered_list":
        # Count numbered items (1. 2. 3. or 1) 2) 3))
        import re
        items = re.findall(r'(?:^|\n)\s*\d+[\.]\s+', content)
        min_items = benchmark.get("min_items", 3)
        
        if len(items) >= min_items:
            score = 1.0
            notes.append(f"Found {len(items)} numbered items (required: {min_items})")
        elif len(items) > 0:
            score = len(items) / min_items
            notes.append(f"Found only {len(items)} items (required: {min_items})")
        else:
            score = 0.3
            notes.append("No numbered list format detected")
    
    elif expected_format == "markdown_table":
        if "|" in content and "---" in content:
            rows = content.count("\n|")
            min_rows = benchmark.get("min_rows", 3)
            if rows >= min_rows:
                score = 1.0
                notes.append(f"Valid markdown table with {rows} rows")
            else:
                score = 0.6
                notes.append(f"Markdown table found but only {rows} rows")
        else:
            score = 0.3
            notes.append("No markdown table format detected")
    
    elif expected_format == "single_sentence":
        sentences = content.count(".") + content.count("!") + content.count("?")
        if sentences <= benchmark.get("max_sentences", 1):
            score = 1.0
            notes.append("Response is appropriately concise")
        else:
            score = 0.5
            notes.append(f"Response has {sentences} sentences (expected 1)")
    
    elif expected_format == "paragraphs":
        paragraphs = len([p for p in content.split("\n\n") if len(p.strip()) > 50])
        min_paragraphs = benchmark.get("min_paragraphs", 3)
        if paragraphs >= min_paragraphs:
            score = 1.0
            notes.append(f"Found {paragraphs} substantial paragraphs")
        else:
            score = paragraphs / min_paragraphs
            notes.append(f"Found only {paragraphs} paragraphs (required: {min_paragraphs})")
    
    elif expected_format == "code_block":
        required = benchmark.get("required_elements", [])
        found = sum(1 for elem in required if elem.lower() in content.lower())
        if found == len(required):
            score = 1.0
            notes.append("All required code elements found")
        else:
            score = found / len(required)
            notes.append(f"Found {found}/{len(required)} required elements")
    
    status = "success" if score >= 0.7 else "partial" if score > 0 else "failure"
    
    return round(score, 2), status, "; ".join(notes)


async def run_all_benchmarks(model_id: str) -> List[Dict[str, Any]]:
    """
    Run all benchmarks on a model.
    
    Args:
        model_id: The OpenRouter model ID.
        
    Returns:
        List of all benchmark results.
    """
    results = []
    for benchmark_type in BENCHMARK_PROMPTS.keys():
        result = await run_benchmark(model_id, benchmark_type)
        results.append(result)
    return results


def get_available_benchmarks() -> List[Dict[str, Any]]:
    """
    Get list of available benchmark types.
    
    Returns:
        List of benchmark metadata.
    """
    return [
        {
            "id": key,
            "type": value["type"],
            "language": value["language"],
            "description": value["prompt"][:100] + "..."
        }
        for key, value in BENCHMARK_PROMPTS.items()
    ]

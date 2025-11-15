"""
LLM interaction using Google Gemini API for contract analysis
Enhanced with better error handling, validation, and rate limiting
"""
import google.generativeai as genai
import json
from typing import Dict, Any, Optional
import logging
import time
from functools import wraps

# Configure logging to show LLM interactions in terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 1  # seconds between API calls
CONTRACT_EXCERPT_LIMIT = 8000
ANALYSIS_EXCERPT_LIMIT = 12000

# Configure Gemini API (will be set from Streamlit app)
_api_key: Optional[str] = None
_last_api_call: float = 0

def rate_limit(func):
    """Decorator to enforce rate limiting between API calls."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        global _last_api_call
        elapsed = time.time() - _last_api_call
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        result = func(*args, **kwargs)
        _last_api_call = time.time()
        return result
    return wrapper


def validate_contract_text(contract_text: str) -> None:
    """Validate contract text input."""
    if not contract_text or not contract_text.strip():
        raise ValueError("Contract text cannot be empty")
    
    if len(contract_text.strip()) < 100:
        raise ValueError("Contract text appears too short to analyze (minimum 100 characters)")


def set_api_key(api_key: str) -> None:
    """Set the Gemini API key with validation."""
    global _api_key
    if not api_key or not api_key.strip():
        raise ValueError("API key cannot be empty")
    if not api_key.startswith('AIza'):
        logger.warning("API key format may be incorrect (expected to start with 'AIza')")
    
    _api_key = api_key.strip()
    genai.configure(api_key=_api_key)
    logger.info("✓ Gemini API key configured successfully")

@rate_limit
def _make_gemini_request(prompt: str, max_retries: int = MAX_RETRIES) -> str:
    """Make a request to Gemini with retry logic."""
    if not _api_key:
        raise ValueError("Gemini API key not set. Please configure your API key first.")
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"API request attempt {attempt + 1}/{max_retries}")
            response = model.generate_content(prompt)
            
            if not response.text or not response.text.strip():
                raise ValueError("Empty response from Gemini API")
                
            return response.text.strip()
            
        except Exception as e:
            logger.warning(f"API attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(1 * (attempt + 1))  # Progressive backoff
    
    raise Exception("All API attempts failed")

def identify_contract_type(contract_text: str) -> Dict[str, Any]:
    """
    Identify the type of contract and provide reasoning with improved error handling.
    
    Args:
        contract_text: Full text extracted from the contract PDF
        
    Returns:
        Dictionary containing contract type and reasoning
        
    Raises:
        ValueError: If contract text is invalid
        Exception: If API call fails after retries
    """
    validate_contract_text(contract_text)
    
    # Limit text for quick analysis
    contract_excerpt = contract_text[:CONTRACT_EXCERPT_LIMIT]
    
    logger.info("=" * 80)
    logger.info("IDENTIFYING CONTRACT TYPE")
    logger.info("=" * 80)
    logger.info(f"Analyzing excerpt: {len(contract_excerpt)} characters")
    
    prompt = f"""You are an expert contract analyst. Analyze this contract and identify its type.

Contract Text:
{contract_excerpt}

Classify the contract into ONE of these types:
- SaaS Subscription (recurring software access)
- Professional Services (consulting, implementation, training)
- Perpetual Software License (one-time software purchase)
- Hybrid (combination of subscription + services)
- Hardware/Equipment Sale
- Maintenance & Support
- Other

Return valid JSON with this structure:
{{
    "contract_type": "the primary contract type from the list above",
    "confidence": "high/medium/low",
    "reasoning": "2-3 sentence explanation of why this is the identified type",
    "key_indicators": ["indicator 1", "indicator 2", "indicator 3"]
}}

Requirements:
- contract_type must be exactly one of the types listed above
- confidence must be exactly "high", "medium", or "low"
- reasoning must be 2-3 complete sentences
- key_indicators must be an array of 1-5 specific text indicators

Respond ONLY with valid JSON, no additional text."""

    try:
        logger.info("Calling Gemini API for contract type identification...")
        response_text = _make_gemini_request(prompt)
        
        logger.info("\n--- CONTRACT TYPE RESPONSE ---")
        logger.info(response_text[:500] + "..." if len(response_text) > 500 else response_text)
        logger.info("--- END RESPONSE ---\n")
        
        result = _parse_json_from_response(response_text)
        _validate_contract_type_response(result)
        
        logger.info(f"✓ Identified as: {result.get('contract_type', 'Unknown')}")
        logger.info(f"  Confidence: {result.get('confidence', 'N/A')}")
        logger.info("=" * 80 + "\n")
        
        return result
        
    except Exception as e:
        logger.error(f"✗ Error identifying contract type: {str(e)}")
        # Return structured fallback
        return {
            'contract_type': 'Other',
            'confidence': 'low',
            'reasoning': f'Could not determine contract type due to analysis error: {str(e)[:100]}',
            'key_indicators': ['Analysis failed', 'Manual review required']
        }


def _validate_contract_type_response(result: Dict[str, Any]) -> None:
    """Validate the structure and content of contract type response."""
    required_fields = ['contract_type', 'confidence', 'reasoning', 'key_indicators']
    
    for field in required_fields:
        if field not in result:
            raise ValueError(f"Missing required field: {field}")
    
    valid_types = [
        'SaaS Subscription', 'Professional Services', 'Perpetual Software License',
        'Hybrid', 'Hardware/Equipment Sale', 'Maintenance & Support', 'Other'
    ]
    if result['contract_type'] not in valid_types:
        logger.warning(f"Unexpected contract type: {result['contract_type']}")
    
    valid_confidence = ['high', 'medium', 'low']
    if result['confidence'] not in valid_confidence:
        logger.warning(f"Invalid confidence level: {result['confidence']}")
    
    if not isinstance(result['key_indicators'], list):
        raise ValueError("key_indicators must be a list")


def _parse_json_from_response(response_text: str) -> Dict[str, Any]:
    """
    Helper function to parse JSON from LLM response with improved error handling.

    Attempts to extract JSON whether it's wrapped in code fences or returned raw.
    Raises json.JSONDecodeError if parsing fails.
    """
    if not response_text:
        raise json.JSONDecodeError("Empty response", "", 0)
    
    text = response_text.strip()
    
    # Try different extraction methods
    extraction_methods = [
        # Method 1: JSON code fence
        lambda t: _extract_between_markers(t, '```json', '```'),
        # Method 2: Generic code fence
        lambda t: _extract_between_markers(t, '```', '```'),
        # Method 3: Curly braces
        lambda t: _extract_json_object(t),
        # Method 4: Raw text
        lambda t: t
    ]
    
    for i, method in enumerate(extraction_methods):
        try:
            candidate = method(text)
            if candidate:
                parsed = json.loads(candidate)
                logger.debug(f"Successfully parsed JSON using method {i+1}")
                return parsed
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"JSON parsing method {i+1} failed: {e}")
            continue
    
    # If all methods fail, provide more context
    raise json.JSONDecodeError(
        f"Could not parse JSON from response. Response preview: {text[:200]}...",
        text,
        0
    )


def _extract_between_markers(text: str, start_marker: str, end_marker: str) -> Optional[str]:
    """Extract text between two markers."""
    if start_marker not in text:
        return None
    
    start_idx = text.find(start_marker) + len(start_marker)
    end_idx = text.find(end_marker, start_idx)
    
    if end_idx == -1:
        return None
    
    return text[start_idx:end_idx].strip()


def _extract_json_object(text: str) -> Optional[str]:
    """Extract JSON object from text by finding matching braces."""
    first_brace = text.find('{')
    if first_brace == -1:
        return None
    
    brace_count = 0
    for i, char in enumerate(text[first_brace:], first_brace):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                return text[first_brace:i+1]
    
    return None


def extract_and_analyze_combined(contract_text: str) -> Dict[str, Any]:
    """
    Combined extraction and analysis in a single LLM call for better performance.
    Enhanced with better error handling and validation.
    
    Args:
        contract_text: Full text extracted from the contract PDF
        
    Returns:
        Dictionary containing both extracted data and ASC 606 analysis
        
    Raises:
        ValueError: If contract text is invalid
        Exception: If analysis fails after retries
    """
    validate_contract_text(contract_text)
    
    # Limit text to reduce token usage
    contract_excerpt = contract_text[:ANALYSIS_EXCERPT_LIMIT]
    
    logger.info("=" * 80)
    logger.info("STARTING COMBINED CONTRACT ANALYSIS")
    logger.info("=" * 80)
    logger.info(f"Contract excerpt length: {len(contract_excerpt)} characters")
    
    prompt = f"""You are an expert contract analyst and accountant specializing in ASC 606 revenue recognition.

Analyze this SaaS contract and provide BOTH contract information extraction AND ASC 606 analysis in a single response.

Contract Text:
{contract_excerpt}

Return valid JSON with this EXACT structure:
{{
    "contract_info": {{
        "customer_name": "company name of the customer (required)",
        "vendor_name": "company name of the vendor/provider (required)",
        "contract_start_date": "YYYY-MM-DD format - extract the actual start/effective date from the contract",
        "contract_end_date": "YYYY-MM-DD format - extract the actual end/termination date from the contract",
        "total_contract_value": 0,
        "payment_terms": "monthly/annual/quarterly (required)",
        "performance_obligations": ["list", "of", "distinct", "services"]
    }},
    "asc606_analysis": {{
        "step_1": {{
            "title": "Identify the Contract",
            "description": "Brief analysis of contract validity and enforceability",
            "details": ["specific point about contract identification", "another point"]
        }},
        "step_2": {{
            "title": "Identify Performance Obligations", 
            "description": "Analysis of distinct goods/services promised",
            "details": ["specific performance obligation", "another obligation"]
        }},
        "step_3": {{
            "title": "Determine Transaction Price",
            "description": "Analysis of total consideration expected",
            "details": ["fixed consideration component", "variable consideration if any"]
        }},
        "step_4": {{
            "title": "Allocate Transaction Price",
            "description": "Allocation methodology and SSP considerations", 
            "details": ["allocation to obligation 1", "allocation to obligation 2"]
        }},
        "step_5": {{
            "title": "Recognize Revenue",
            "description": "Revenue recognition timing and pattern",
            "details": ["recognition timing for obligation 1", "recognition timing for obligation 2"]
        }}
    }}
}}

Critical Requirements:
- All dates must be in YYYY-MM-DD format
- total_contract_value must be a numeric value (no currency symbols)
- Each step must have title, description, and details array
- Respond ONLY with valid JSON, no additional text"""

    logger.info("\n--- PROMPT SENT TO LLM ---")
    logger.info(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    logger.info("--- END PROMPT ---\n")

    try:
        logger.info("Calling Gemini API (gemini-2.0-flash)...")
        response_text = _make_gemini_request(prompt)
        
        logger.info("\n--- RAW LLM RESPONSE ---")
        logger.info(response_text[:1000] + "..." if len(response_text) > 1000 else response_text)
        logger.info("--- END RESPONSE ---\n")
        
        logger.info("Parsing JSON response...")
        result = _parse_json_from_response(response_text)
        _validate_combined_analysis_response(result)
        logger.info("✓ JSON parsed and validated successfully")
        
        logger.info("\n--- EXTRACTED CONTRACT INFO ---")
        contract_info = result.get('contract_info', {})
        logger.info(f"Customer: {contract_info.get('customer_name', 'N/A')}")
        logger.info(f"Vendor: {contract_info.get('vendor_name', 'N/A')}")
        logger.info(f"Value: ${contract_info.get('total_contract_value', 'N/A')}")
        logger.info(f"Start: {contract_info.get('contract_start_date', 'N/A')}")
        logger.info(f"End: {contract_info.get('contract_end_date', 'N/A')}")
        logger.info("--- END CONTRACT INFO ---\n")
        
        # Generate revenue schedule
        logger.info("Generating revenue schedule...")
        from utils.asc606_engine import generate_revenue_schedule
        revenue_schedule = generate_revenue_schedule(result['contract_info'])
        result['asc606_analysis']['revenue_schedule'] = revenue_schedule
        logger.info(f"✓ Generated {len(revenue_schedule)} revenue periods")
        
        logger.info("=" * 80)
        logger.info("ANALYSIS COMPLETE")
        logger.info("=" * 80 + "\n")
        
        return result
        
    except Exception as e:
        logger.error(f"✗ Error during analysis: {str(e)}", exc_info=True)
        raise Exception(f"Combined analysis failed: {str(e)[:200]}...")


def _validate_combined_analysis_response(result: Dict[str, Any]) -> None:
    """Validate the structure and content of combined analysis response."""
    # Check top-level structure
    required_top_level = ['contract_info', 'asc606_analysis']
    for field in required_top_level:
        if field not in result:
            raise ValueError(f"Missing top-level field: {field}")
    
    # Validate contract info
    contract_info = result['contract_info']
    required_contract_fields = [
        'customer_name', 'vendor_name', 'contract_start_date', 
        'contract_end_date', 'total_contract_value', 'payment_terms'
    ]
    
    for field in required_contract_fields:
        if field not in contract_info:
            raise ValueError(f"Missing contract_info field: {field}")
    
    # Validate date formats
    date_fields = ['contract_start_date', 'contract_end_date']
    for field in date_fields:
        date_str = contract_info.get(field, '')
        # Allow N/A or empty for missing dates
        if date_str in ['N/A', '', None]:
            logger.warning(f"{field} is missing or N/A - marking as unable to identify")
            contract_info[field] = 'Unable to identify'
        elif not _is_valid_date_format(date_str):
            logger.warning(f"Invalid date format for {field}: {date_str} - marking as unable to identify")
            contract_info[field] = 'Unable to identify'
    
    # Validate ASC 606 analysis structure
    asc606 = result['asc606_analysis']
    for step_num in range(1, 6):
        step_key = f"step_{step_num}"
        if step_key not in asc606:
            raise ValueError(f"Missing ASC 606 step: {step_key}")
        
        step_data = asc606[step_key]
        for required_field in ['title', 'description', 'details']:
            if required_field not in step_data:
                raise ValueError(f"Missing field '{required_field}' in {step_key}")


def _is_valid_date_format(date_str: str) -> bool:
    """Check if date string matches YYYY-MM-DD format."""
    if not date_str or len(date_str) != 10:
        return False
    
    try:
        parts = date_str.split('-')
        if len(parts) != 3:
            return False
        
        year, month, day = parts
        return (len(year) == 4 and year.isdigit() and 
                len(month) == 2 and month.isdigit() and
                len(day) == 2 and day.isdigit() and
                1 <= int(month) <= 12 and
                1 <= int(day) <= 31)
    except (ValueError, AttributeError):
        return False
from typing import List, Dict, Any
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

"""
ASC 606 Revenue Recognition Engine
Implements the 5-step model for revenue recognition with enhanced error handling and validation
"""

logger = logging.getLogger(__name__)

def _is_valid_yyyy_mm_dd(date_str: str) -> bool:
    """Validate if a date string is in YYYY-MM-DD format."""
    try:
        if not date_str or date_str in ['Unable to identify', 'N/A']:
            return False
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except Exception:
        return False


def validate_contract_data(contract_data: Dict[str, Any]) -> None:
    """Validate contract data before generating revenue schedule."""
    required_fields = ['contract_start_date', 'contract_end_date', 'total_contract_value', 'payment_terms']
    
    for field in required_fields:
        if field not in contract_data:
            raise ValueError(f"Missing required field: {field}")
        
        # Allow empty values for dates if they couldn't be extracted
        if field in ['contract_start_date', 'contract_end_date']:
            value = str(contract_data[field]).strip()
            if not value or value in ['', 'Unable to identify', 'N/A']:
                logger.warning(f"Field '{field}' is empty or unable to identify")
                continue
        else:
            if not contract_data[field] or str(contract_data[field]).strip() == '':
                raise ValueError(f"Field '{field}' cannot be empty")
    
    # Validate dates only if both are present and in valid format
    start_date_str = str(contract_data.get('contract_start_date', '')).strip()
    end_date_str = str(contract_data.get('contract_end_date', '')).strip()

    if _is_valid_yyyy_mm_dd(start_date_str) and _is_valid_yyyy_mm_dd(end_date_str):
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        if start_date >= end_date:
            raise ValueError("Contract start date must be before end date")
    else:
        if start_date_str and not _is_valid_yyyy_mm_dd(start_date_str):
            logger.warning(f"Field 'contract_start_date' has invalid format: '{start_date_str}' (expected YYYY-MM-DD)")
        if end_date_str and not _is_valid_yyyy_mm_dd(end_date_str):
            logger.warning(f"Field 'contract_end_date' has invalid format: '{end_date_str}' (expected YYYY-MM-DD)")
    
    # Validate contract value
    try:
        total_value = float(contract_data['total_contract_value'])
        if total_value <= 0:
            raise ValueError("Contract value must be greater than 0")
    except (ValueError, TypeError):
        raise ValueError("Invalid contract value. Must be a positive number")


def calculate_duration_months(start_date: datetime, end_date: datetime) -> int:
    """Calculate contract duration in months (inclusive)."""
    duration_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if end_date.day >= start_date.day:
        duration_months += 1
    return max(1, duration_months)


def generate_revenue_schedule(contract_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate revenue recognition schedule based on contract data.
    
    Implements ASC 606 Step 5: Recognize revenue when (or as) 
    performance obligations are satisfied.
    
    Args:
        contract_data: Extracted contract information with optional 'obligations' list
                      or 'performance_obligations' list (legacy format)
        
    Returns:
        List of dictionaries containing revenue schedule by period
        
    Raises:
        ValueError: If contract data is invalid
    """
    logger.info("Generating revenue schedule...")
    
    try:
        validate_contract_data(contract_data)
        

        # Check if dates are available and valid
        start_date_str = str(contract_data.get('contract_start_date', '')).strip()
        end_date_str = str(contract_data.get('contract_end_date', '')).strip()

        if not _is_valid_yyyy_mm_dd(start_date_str) or not _is_valid_yyyy_mm_dd(end_date_str):
            logger.warning(f"Invalid or missing contract dates: start='{start_date_str}', end='{end_date_str}' - cannot generate revenue schedule")
            return [{
                'period': 'Unable to identify',
                'period_start': start_date_str or 'Unable to identify',
                'period_end': end_date_str or 'Unable to identify',
                'revenue_amount': 0,
                'deferred_revenue': 0,
                'note': 'Contract dates missing or invalid format (expected YYYY-MM-DD)'
            }]

        # Parse dates and values
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        total_value = float(contract_data['total_contract_value'])
        payment_terms = str(contract_data.get('payment_terms', 'monthly')).lower().strip()

        logger.info(f"Contract period: {start_date.date()} to {end_date.date()}")
        logger.info(f"Total value: ${total_value:,.2f}")
        logger.info(f"Payment terms: {payment_terms}")

        duration_months = calculate_duration_months(start_date, end_date)
        logger.info(f"Duration: {duration_months} months")

        # Ignore pricing_schedule: always generate monthly schedule

        # Check for multi-obligation scenario
        obligations = contract_data.get('obligations')
        logger.info(f"Checking for obligations: {obligations}")
        logger.info(f"Obligations type: {type(obligations)}")

        if obligations and isinstance(obligations, list) and len(obligations) > 0:
            # Validate that obligations have proper structure
            if all(isinstance(ob, dict) and 'name' in ob and 'allocated_value' in ob for ob in obligations):
                logger.info(f"✓ Processing {len(obligations)} performance obligations")
                logger.info(f"Obligation details: {obligations}")
                return _generate_multi_obligation_schedule(
                    start_date, end_date, obligations, duration_months
                )
            else:
                logger.warning("Obligations found but not properly structured, falling back to single obligation")
        else:
            logger.info("No obligations found, using single-obligation schedule")

        # Single obligation - use payment terms
        return _generate_single_obligation_schedule(
            start_date, end_date, total_value, duration_months, payment_terms
        )
        
    except Exception as e:
        logger.error(f"Error generating revenue schedule: {str(e)}")
        return [{
            'period': 'Error',
            'period_start': 'N/A',
            'period_end': 'N/A',
            'revenue_amount': 0,
            'deferred_revenue': 0,
            'error': str(e)
        }]


def _generate_multi_obligation_schedule(
    start_date: datetime,
    end_date: datetime,
    obligations: List[Dict[str, Any]],
    duration_months: int
) -> List[Dict[str, Any]]:
    """
    Generate revenue schedule for multiple performance obligations.
    
    Supports:
    - over_time: Revenue recognized evenly over contract duration
    - point_in_time: Revenue recognized in specific period
    - upfront: Revenue recognized in first period
    """
    schedule = []
    months = [start_date + relativedelta(months=i) for i in range(duration_months)]
    
    # Track cumulative recognized revenue per obligation for deferred calculation
    recognized_by_obligation = [0.0] * len(obligations)
    
    # Build reasoning for the schedule
    reasoning_parts = ["Multi-obligation revenue schedule:"]
    for ob in obligations:
        ob_name = ob.get('name', 'unknown')
        ob_value = float(ob.get('allocated_value', 0))
        ob_recognition = ob.get('recognition', 'over_time').lower()
        
        if ob_recognition == 'over_time':
            monthly_amount = ob_value / duration_months
            reasoning_parts.append(
                f"• {ob_name.replace('_', ' ').title()}: ${ob_value:,.2f} recognized over time "
                f"(${monthly_amount:,.2f}/month for {duration_months} months per ASC 606 - "
                f"performance obligation satisfied evenly over contract term)"
            )
        elif ob_recognition == 'point_in_time':
            recognition_period = ob.get('recognition_period', 2)
            reasoning_parts.append(
                f"• {ob_name.replace('_', ' ').title()}: ${ob_value:,.2f} recognized at point in time "
                f"(month {recognition_period}) per ASC 606 - performance obligation satisfied upon completion/delivery"
            )
        elif ob_recognition == 'upfront':
            reasoning_parts.append(
                f"• {ob_name.replace('_', ' ').title()}: ${ob_value:,.2f} recognized upfront "
                f"(month 1) per ASC 606 - performance obligation satisfied immediately"
            )
    
    reasoning = "\n".join(reasoning_parts)
    logger.info(f"\n{reasoning}\n")
    
    for month_idx, month_start in enumerate(months):
        period = month_start.strftime('%Y-%m')
        period_start = month_start.strftime('%Y-%m-%d')
        
        # Calculate period end
        period_end = month_start + relativedelta(months=1) - timedelta(days=1)
        if period_end > end_date:
            period_end = end_date
        period_end_str = period_end.strftime('%Y-%m-%d')
        
        # Initialize period record
        period_record = {
            'period': period,
            'period_start': period_start,
            'period_end': period_end_str
        }
        
        period_total_revenue = 0.0
        
        # Process each obligation
        for ob_idx, obligation in enumerate(obligations):
            ob_name = obligation.get('name', f'obligation_{ob_idx + 1}')
            ob_value = float(obligation.get('allocated_value', 0))
            ob_recognition = obligation.get('recognition', 'over_time').lower()
            
            revenue_key = f"revenue_{ob_name}"
            period_revenue = 0.0
            
            # Calculate revenue based on recognition pattern
            if ob_recognition == 'over_time':
                # Recognize evenly over contract duration
                period_revenue = round(ob_value / duration_months, 2)
                
            elif ob_recognition == 'point_in_time':
                # Recognize in specific period (default: month 2 for implementation)
                recognition_period = obligation.get('recognition_period', 2)
                if (month_idx + 1) == recognition_period:
                    period_revenue = round(ob_value, 2)
                    
            elif ob_recognition == 'upfront':
                # Recognize entirely in first period
                if month_idx == 0:
                    period_revenue = round(ob_value, 2)
            
            else:
                logger.warning(f"Unknown recognition pattern '{ob_recognition}' for {ob_name}, treating as over_time")
                period_revenue = round(ob_value / duration_months, 2)
            
            # Record obligation revenue
            period_record[revenue_key] = period_revenue
            recognized_by_obligation[ob_idx] += period_revenue
            period_total_revenue += period_revenue
        
        # Calculate total revenue and deferred revenue for period
        period_record['revenue_amount'] = round(period_total_revenue, 2)
        
        # Deferred revenue = sum of (allocated - recognized so far) for all obligations
        total_deferred = sum(
            max(0, float(ob['allocated_value']) - recognized_by_obligation[idx])
            for idx, ob in enumerate(obligations)
        )
        period_record['deferred_revenue'] = round(total_deferred, 2)
        
        # Add reasoning to first period only
        if month_idx == 0:
            period_record['_reasoning'] = reasoning
        
        schedule.append(period_record)
    
    return schedule


def _generate_single_obligation_schedule(
    start_date: datetime,
    end_date: datetime,
    total_value: float,
    duration_months: int,
    payment_terms: str
) -> List[Dict[str, Any]]:
    """Generate revenue schedule for single obligation based on payment terms."""
    
    # Always use monthly schedule regardless of payment terms
    logger.info(f"Using monthly recognition: ${total_value:,.2f} recognized over {duration_months} months (${total_value/duration_months:,.2f}/month)")
    return _generate_monthly_schedule(start_date, end_date, total_value, duration_months)


def _generate_monthly_schedule(
    start_date: datetime,
    end_date: datetime,
    total_value: float,
    duration_months: int
) -> List[Dict[str, Any]]:
    """Generate monthly revenue schedule."""
    logger.debug("Generating monthly revenue schedule")
    schedule = []
    monthly_revenue = round(total_value / duration_months, 2)
    
    reasoning = (
        f"Single obligation recognized over time per ASC 606:\n"
        f"• Total contract value: ${total_value:,.2f}\n"
        f"• Contract duration: {duration_months} months\n"
        f"• Monthly revenue: ${monthly_revenue:,.2f} (${total_value:,.2f} ÷ {duration_months} months)\n"
        f"• Recognition pattern: Revenue recognized evenly as performance obligation is satisfied over contract term"
    )
    
    current_date = start_date
    for month in range(duration_months):
        period_end = current_date + relativedelta(months=1) - timedelta(days=1)
        if period_end > end_date:
            period_end = end_date
        
        remaining_value = total_value - (monthly_revenue * (month + 1))
        
        record = {
            'period': current_date.strftime('%Y-%m'),
            'period_start': current_date.strftime('%Y-%m-%d'),
            'period_end': period_end.strftime('%Y-%m-%d'),
            'revenue_amount': monthly_revenue,
            'deferred_revenue': round(max(0, remaining_value), 2)
        }
        
        # Add reasoning to first period
        if month == 0:
            record['_reasoning'] = reasoning
        
        schedule.append(record)
        
        current_date += relativedelta(months=1)
        if current_date > end_date:
            break
    
    return schedule


def _generate_annual_schedule(
    start_date: datetime,
    end_date: datetime,
    total_value: float,
    duration_months: int
) -> List[Dict[str, Any]]:
    """Generate annual revenue schedule."""
    logger.debug("Generating annual revenue schedule")
    schedule = []
    years = max(1, duration_months // 12)
    annual_revenue = round(total_value / years, 2)
    
    reasoning = (
        f"Single obligation recognized over time per ASC 606:\n"
        f"• Total contract value: ${total_value:,.2f}\n"
        f"• Contract duration: {years} year(s)\n"
        f"• Annual revenue: ${annual_revenue:,.2f} (${total_value:,.2f} ÷ {years} years)\n"
        f"• Recognition pattern: Revenue recognized annually as performance obligation is satisfied over contract term"
    )
    
    current_date = start_date
    for year in range(years):
        period_end = current_date + relativedelta(years=1) - timedelta(days=1)
        if period_end > end_date:
            period_end = end_date
        
        remaining_value = total_value - (annual_revenue * (year + 1))
        
        record = {
            'period': current_date.strftime('%Y'),
            'period_start': current_date.strftime('%Y-%m-%d'),
            'period_end': period_end.strftime('%Y-%m-%d'),
            'revenue_amount': annual_revenue,
            'deferred_revenue': round(max(0, remaining_value), 2)
        }
        
        # Add reasoning to first period
        if year == 0:
            record['_reasoning'] = reasoning
        
        schedule.append(record)
        
        current_date += relativedelta(years=1)
        if current_date > end_date:
            break
    
    return schedule


def _generate_quarterly_schedule(
    start_date: datetime,
    end_date: datetime,
    total_value: float,
    duration_months: int
) -> List[Dict[str, Any]]:
    """Generate quarterly revenue schedule."""
    logger.debug("Generating quarterly revenue schedule")
    schedule = []
    quarters = max(1, duration_months // 3)
    quarterly_revenue = round(total_value / quarters, 2)
    
    reasoning = (
        f"Single obligation recognized over time per ASC 606:\n"
        f"• Total contract value: ${total_value:,.2f}\n"
        f"• Contract duration: {quarters} quarter(s)\n"
        f"• Quarterly revenue: ${quarterly_revenue:,.2f} (${total_value:,.2f} ÷ {quarters} quarters)\n"
        f"• Recognition pattern: Revenue recognized quarterly as performance obligation is satisfied over contract term"
    )
    
    current_date = start_date
    for quarter in range(quarters):
        period_end = current_date + relativedelta(months=3) - timedelta(days=1)
        if period_end > end_date:
            period_end = end_date
        
        remaining_value = total_value - (quarterly_revenue * (quarter + 1))
        quarter_num = (current_date.month - 1) // 3 + 1
        
        record = {
            'period': f"{current_date.strftime('%Y')}-Q{quarter_num}",
            'period_start': current_date.strftime('%Y-%m-%d'),
            'period_end': period_end.strftime('%Y-%m-%d'),
            'revenue_amount': quarterly_revenue,
            'deferred_revenue': round(max(0, remaining_value), 2)
        }
        
        # Add reasoning to first period
        if quarter == 0:
            record['_reasoning'] = reasoning
        
        schedule.append(record)
        
        current_date += relativedelta(months=3)
        if current_date > end_date:
            break
    
    return schedule
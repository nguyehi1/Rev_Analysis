"""
ASC 606 Revenue Recognition Engine
Implements the 5-step model for revenue recognition with enhanced error handling and validation
"""
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

def validate_contract_data(contract_data: Dict[str, Any]) -> None:
    """Validate contract data before generating revenue schedule."""
    required_fields = ['contract_start_date', 'contract_end_date', 'total_contract_value', 'payment_terms']
    
    for field in required_fields:
        if field not in contract_data:
            raise ValueError(f"Missing required field: {field}")
        
        # Allow empty values or "Unable to identify" for dates if they couldn't be extracted
        if field in ['contract_start_date', 'contract_end_date']:
            value = str(contract_data[field]).strip()
            if not value or value in ['', 'Unable to identify', 'N/A']:
                logger.warning(f"Field '{field}' is empty or unable to identify - revenue schedule may be incomplete")
                continue
        else:
            if not contract_data[field] or str(contract_data[field]).strip() == '':
                raise ValueError(f"Field '{field}' cannot be empty")
    
    # Validate dates only if both are present
    if contract_data.get('contract_start_date') and contract_data.get('contract_end_date'):
        try:
            start_date = datetime.strptime(str(contract_data['contract_start_date']), '%Y-%m-%d')
            end_date = datetime.strptime(str(contract_data['contract_end_date']), '%Y-%m-%d')
            
            if start_date >= end_date:
                raise ValueError("Contract start date must be before end date")
                
        except ValueError as e:
            if "time data" in str(e):
                raise ValueError("Invalid date format. Expected YYYY-MM-DD")
            raise
    
    # Validate contract value
    try:
        total_value = float(contract_data['total_contract_value'])
        if total_value <= 0:
            raise ValueError("Contract value must be greater than 0")
    except (ValueError, TypeError):
        raise ValueError("Invalid contract value. Must be a positive number")

def generate_revenue_schedule(contract_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate revenue recognition schedule based on contract data with enhanced validation.
    
    Implements ASC 606 Step 5: Recognize revenue when (or as) 
    performance obligations are satisfied.
    
    Args:
        contract_data: Extracted contract information
        
    Returns:
        List of dictionaries containing revenue schedule by period
        
    Raises:
        ValueError: If contract data is invalid
    """
    logger.info("Generating revenue schedule...")
    
    try:
        validate_contract_data(contract_data)
        
        # Check if dates are available
        start_date_str = str(contract_data.get('contract_start_date', '')).strip()
        end_date_str = str(contract_data.get('contract_end_date', '')).strip()
        
        if not start_date_str or start_date_str in ['Unable to identify', 'N/A'] or \
           not end_date_str or end_date_str in ['Unable to identify', 'N/A']:
            logger.warning("Contract dates are missing - cannot generate revenue schedule")
            return [{
                'period': 'Unable to identify',
                'period_start': 'Unable to identify',
                'period_end': 'Unable to identify',
                'revenue_amount': 0,
                'deferred_revenue': 0,
                'note': 'Contract dates not found in document'
            }]
        
        # Parse dates with validation
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        total_value = float(contract_data['total_contract_value'])
        payment_terms = str(contract_data.get('payment_terms', 'monthly')).lower().strip()
        
        logger.info(f"Contract period: {start_date.date()} to {end_date.date()}")
        logger.info(f"Total value: ${total_value:,.2f}")
        logger.info(f"Payment terms: {payment_terms}")
        
        # Calculate contract duration in months
        duration_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
        
        # Ensure minimum duration
        if duration_months <= 0:
            logger.warning("Invalid duration calculated, defaulting to 12 months")
            duration_months = 12
        
        logger.info(f"Duration: {duration_months} months")
        
        # Generate schedule based on payment terms
        if any(term in payment_terms for term in ['month', 'monthly']):
            return _generate_monthly_schedule(start_date, end_date, total_value, duration_months)
        elif any(term in payment_terms for term in ['annual', 'year', 'yearly']):
            return _generate_annual_schedule(start_date, end_date, total_value, duration_months)
        elif any(term in payment_terms for term in ['quarter', 'quarterly']):
            return _generate_quarterly_schedule(start_date, end_date, total_value, duration_months)
        else:
            logger.warning(f"Unrecognized payment terms '{payment_terms}', defaulting to monthly")
            return _generate_monthly_schedule(start_date, end_date, total_value, duration_months)
        
    except Exception as e:
        logger.error(f"Error generating revenue schedule: {str(e)}")
        # Return error schedule for debugging
        return [{
            'period': 'Error',
            'period_start': 'N/A',
            'period_end': 'N/A',
            'revenue_amount': 0,
            'deferred_revenue': 0,
            'error': str(e)
        }]


def _generate_monthly_schedule(start_date: datetime, end_date: datetime, total_value: float, duration_months: int) -> List[Dict[str, Any]]:
    """Generate monthly revenue schedule."""
    logger.debug("Generating monthly revenue schedule")
    schedule = []
    monthly_revenue = total_value / duration_months
    
    current_date = start_date
    for month in range(duration_months):
        period_end = current_date + relativedelta(months=1) - timedelta(days=1)
        # Ensure we don't go past the contract end date
        if period_end > end_date:
            period_end = end_date
        
        remaining_value = total_value - (monthly_revenue * (month + 1))
        
        schedule.append({
            'period': current_date.strftime('%Y-%m'),
            'period_start': current_date.strftime('%Y-%m-%d'),
            'period_end': period_end.strftime('%Y-%m-%d'),
            'revenue_amount': round(monthly_revenue, 2),
            'deferred_revenue': round(max(0, remaining_value), 2)
        })
        
        current_date += relativedelta(months=1)
        if current_date > end_date:
            break
    
    return schedule

def _generate_annual_schedule(start_date: datetime, end_date: datetime, total_value: float, duration_months: int) -> List[Dict[str, Any]]:
    """Generate annual revenue schedule."""
    logger.debug("Generating annual revenue schedule")
    schedule = []
    years = max(1, duration_months // 12)
    annual_revenue = total_value / years
    
    current_date = start_date
    for year in range(years):
        period_end = current_date + relativedelta(years=1) - timedelta(days=1)
        # Ensure we don't go past the contract end date
        if period_end > end_date:
            period_end = end_date
        
        remaining_value = total_value - (annual_revenue * (year + 1))
        
        schedule.append({
            'period': current_date.strftime('%Y'),
            'period_start': current_date.strftime('%Y-%m-%d'),
            'period_end': period_end.strftime('%Y-%m-%d'),
            'revenue_amount': round(annual_revenue, 2),
            'deferred_revenue': round(max(0, remaining_value), 2)
        })
        
        current_date += relativedelta(years=1)
        if current_date > end_date:
            break
    
    return schedule

def _generate_quarterly_schedule(start_date: datetime, end_date: datetime, total_value: float, duration_months: int) -> List[Dict[str, Any]]:
    """Generate quarterly revenue schedule."""
    logger.debug("Generating quarterly revenue schedule")
    schedule = []
    quarters = max(1, duration_months // 3)
    quarterly_revenue = total_value / quarters
    
    current_date = start_date
    for quarter in range(quarters):
        period_end = current_date + relativedelta(months=3) - timedelta(days=1)
        # Ensure we don't go past the contract end date
        if period_end > end_date:
            period_end = end_date
        
        remaining_value = total_value - (quarterly_revenue * (quarter + 1))
        quarter_num = (current_date.month - 1) // 3 + 1
        
        schedule.append({
            'period': f"{current_date.strftime('%Y')}-Q{quarter_num}",
            'period_start': current_date.strftime('%Y-%m-%d'),
            'period_end': period_end.strftime('%Y-%m-%d'),
            'revenue_amount': round(quarterly_revenue, 2),
            'deferred_revenue': round(max(0, remaining_value), 2)
        })
        
        current_date += relativedelta(months=3)
        if current_date > end_date:
            break
    
    return schedule
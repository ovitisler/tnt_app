from datetime import datetime

def find_column_index(worksheet, header_name):
    """Find the index of a column by its header name"""
    headers = worksheet.row_values(1)  # Get headers from first row
    try:
        return headers.index(header_name) + 1  # Convert to 1-based index
    except ValueError:
        return None

def parse_date_string(date_str):
    """Parse a date string in either ISO or readable format"""
    if 'T' in str(date_str):
        # Parse ISO format (2025-09-17T00:00:00.000Z)
        return datetime.fromisoformat(str(date_str).replace('Z', '+00:00')).date()
    else:
        # Parse readable format (September 17, 2025)
        return datetime.strptime(str(date_str), '%B %d, %Y').date()

def dates_match(date1, date2):
    """Check if two dates match, handling different formats"""
    if not date1 or not date2:
        return False
    
    try:
        parsed_date1 = parse_date_string(date1)
        parsed_date2 = parse_date_string(date2)
        return parsed_date1 == parsed_date2
    except:
        return str(date1) == str(date2)
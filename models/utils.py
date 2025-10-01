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

def find_day_by_date(schedule_data, date_str):
    """Find schedule entry by date string"""
    for entry in schedule_data:
        if dates_match(entry.get('Date'), date_str):
            return entry
    return None

def date_to_url(date_str):
    """Convert date string to URL-safe format (YYYY-MM-DD)"""
    try:
        # Parse various date formats and convert to YYYY-MM-DD
        if 'T' in str(date_str):
            # ISO format (2025-09-17T00:00:00.000Z)
            dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        elif ',' in date_str:
            # "September 17, 2025" format
            dt = datetime.strptime(date_str, '%B %d, %Y')
        else:
            # Try other common formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            else:
                return date_str  # Return as-is if can't parse
        return dt.strftime('%Y-%m-%d')
    except:
        return date_str

def url_to_date(url_date):
    """Convert URL date (YYYY-MM-DD) back to display format"""
    try:
        dt = datetime.strptime(url_date, '%Y-%m-%d')
        return dt.strftime('%B %d, %Y')
    except:
        return url_date
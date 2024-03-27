import frappe
from datetime import datetime, timedelta

@frappe.whitelist(allow_guest=True)
def get_top_items(days_back=30, top_limit=30):
    # Ensure input parameters are integers
    days_back = int(days_back)
    top_limit = int(top_limit)
    
    # Format today's date as YYYYMMDD
    today_str = datetime.today().strftime('%Y%m%d')

    # Construct a unique cache key based on parameters and today's date
    cache_key = f"top_{top_limit}_items_last_{days_back}_days_as_of_{today_str}"

    # Try to get cached data
    cached_data = frappe.cache().get_value(cache_key)
    if cached_data:
        return cached_data

    # If not cached, calculate the date range
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days_back)

    # Query for top items in submitted Sales Orders within the date range
    query = """
    SELECT item_code, SUM(qty) AS total_qty
    FROM `tabSales Order Item`
    WHERE docstatus = 1 AND creation BETWEEN %s AND %s
    GROUP BY item_code
    ORDER BY total_qty DESC
    LIMIT %s
    """
    top_items = frappe.db.sql(query, (start_date, end_date, top_limit), as_dict=True)

    # Cache the result
    frappe.cache().set_value(cache_key, top_items, expires_in_sec=86400)

    return top_items

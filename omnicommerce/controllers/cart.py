import frappe

@frappe.whitelist(allow_guest=True)
def get_shipping_rules(country=None, totalPrice=None):
    """Fetch shipping rules based on country and price or the entire list if no filters."""

    # Define base query for Shipping Rule
    base_query = """
        SELECT DISTINCT `tabShipping Rule`.name   AS shipping_rule , `tabShipping Rule`.*
        FROM `tabShipping Rule`
        LEFT JOIN `tabShipping Rule Condition` ON `tabShipping Rule Condition`.parent = `tabShipping Rule`.name
        LEFT JOIN `tabShipping Rule Country` ON `tabShipping Rule Country`.parent = `tabShipping Rule`.name
        WHERE `tabShipping Rule`.disabled = 0 AND `tabShipping Rule`.disabled ='Selling'
    """

    # Append condition if either country or price is provided
    conditions = []
    if country:
        conditions.append(f"(`tabShipping Rule Country`.country = {frappe.db.escape(country)} OR `tabShipping Rule Country`.country IS NULL)")
    if conditions:
        where_conditions = " AND ".join(conditions)
        base_query += f" AND {where_conditions}"

    # Execute base query
    shipping_rules = frappe.db.sql(base_query, as_dict=True)

    result = []
    # Fetch associated countries and price ranges for each shipping rule
    for rule in shipping_rules:
        countries = [d.country for d in frappe.get_all("Shipping Rule Country", filters={'parent': rule['shipping_rule']}, fields=['country'])] or [None]
        conditions = frappe.get_all("Shipping Rule Condition", filters={'parent': rule['shipping_rule']}, fields=['shipping_amount','from_value', 'to_value']) or [{'from_value': None, 'to_value': None}]

        for country in countries:
            for condition in conditions:
                # If totalPrice is defined, check if it's within the current condition's range
                if totalPrice:
                    # Default values for from_val and to_val when they are None
                    from_val = condition.get('from_value') or 0
                    to_val = condition.get('to_value') or 0
                    
                    # Skip this condition if totalPrice isn't within the range
                    if not (from_val <= float(totalPrice) and (to_val >= float(totalPrice) or to_val == 0)):
                        continue
                    
                    result.append({
                        "shipping_rule": rule['shipping_rule'],
                        "label": rule['label'],
                        "generic_shipping_amount": rule.get('shipping_amount', 0),
                        "shipping_amount": condition.get('shipping_amount', 0),
                        "country": country if country else "ALL",
                        "price_range_from": condition.get('from_value', 0) if condition.get('from_value', 0) else 0,
                        "price_range_to": condition.get('to_value', 0) if condition.get('from_value', 0) else 0,
                    })

    return {"data": result}


@frappe.whitelist(allow_guest=True)
def get_deliverable_countries():
    # Assuming there's a field in 'Country' doctype indicating deliverability
    countries = frappe.get_all('Country', filters={'custom_is_deliverable': 1}, fields=['name' ,'code'])
    return countries
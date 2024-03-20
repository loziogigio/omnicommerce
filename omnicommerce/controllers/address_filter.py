
import frappe


from webshop.webshop.shopping_cart.cart import  _set_price_list

@frappe.whitelist(allow_guest=True, methods=['POST'])
def validate_adress_filter(limit=None, page=1, filters=None):
    return True
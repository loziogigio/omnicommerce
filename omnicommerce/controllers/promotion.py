import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def apply_coupon_code(quotation_name, applied_code, applied_referral_sales_partner):
    try:
        if not applied_code:
            frappe.throw(_("Please enter a coupon code"))

        coupon_list = frappe.get_all("Coupon Code", filters={"coupon_code": applied_code})
        if not coupon_list:
            frappe.throw(_("Please enter a valid coupon code"))

        coupon_name = coupon_list[0].name

        from erpnext.accounts.doctype.pricing_rule.utils import validate_coupon_code

        validate_coupon_code(coupon_name)
        quotation = frappe.get_doc("Quotation", quotation_name)
        quotation.coupon_code = coupon_name
        quotation.flags.ignore_permissions = True
        quotation.save()

        if applied_referral_sales_partner:
            sales_partner_list = frappe.get_all(
                "Sales Partner", filters={"referral_code": applied_referral_sales_partner}
            )
            if sales_partner_list:
                sales_partner_name = sales_partner_list[0].name
                quotation.referral_sales_partner = sales_partner_name
                quotation.flags.ignore_permissions = True
                quotation.save()

        return quotation

    except Exception as e:
        # Convert the error to a string and log the error
        frappe.log_error(str(e), "Error applying coupon code")

        # Return a formatted API response
        response = {
            "status": "error",
            "message": str(e)
        }
        return response

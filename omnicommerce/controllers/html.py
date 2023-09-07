import frappe
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations as ConfigurationsB2C
from mymb_ecommerce.settings.configurations import Configurations as ConfigurationsB2B


@frappe.whitelist(allow_guest=True)
def get_footers():
    config_b2c = ConfigurationsB2C()
    footer_b2c_html = config_b2c.doc.footer_b2c_html
    config_b2b = ConfigurationsB2B()
    footer_b2b_html = config_b2b.doc.footer_b2b_html

    return {
        "data":{
            "footer_b2c_html":footer_b2c_html,
            "footer_b2b_html":footer_b2b_html,
        }
    }

# @frappe.whitelist(allow_guest=True)
# def get_logos():


    
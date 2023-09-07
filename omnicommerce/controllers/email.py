import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def send_sales_order_confirmation_email(sales_order=None, name=None):
    # Check if neither sales_order nor name is provided
    if not sales_order and not name:
        return {"status": "Failed", "message": "Missing required parameters."}

    # If only name is provided, fetch the Sales Order
    if not sales_order and name:
        sales_order = frappe.get_doc("Sales Order", name)

    # If there's still no sales_order at this point, return failure
    if not sales_order:
        return {"status": "Failed", "message": "Unable to fetch Sales Order."}

    # Fetch email template
    email_template = frappe.get_doc("Email Template", "sales-order-confirmation")

    # Set the email recipients, fetching from the Sales Order customer's details
    recipients = [sales_order.recipient_email]  # Assuming 'email_id' is the field in Sales Order for customer's email

    # Generate PDF of the Sales Order
    # pdf_data = frappe.attach_print(doctype="Sales Order", name=sales_order.name, file_name=F"sales_order.pdf")

    # Send email
    frappe.sendmail(
        recipients=recipients,
        subject=email_template.subject,
        message=email_template.response,
        # attachments=[pdf_data],
        reference_doctype=sales_order.doctype,
        reference_name=sales_order.name
    )

    return {"status": "Success", "message": "Email sent successfully."}

import frappe
from frappe import _
from omnicommerce.controllers.pdf import get_pdf_data
from omnicommerce.controllers.pdf import get_default_letterhead

@frappe.whitelist(allow_guest=True)
def send_sales_order_confirmation_email(sales_order=None, name=None , attachment=True , recipients=None):
    # Check if neither sales_order nor name is provided
    doc_name = "Sales Order"
    if not sales_order and not name:
        return {"status": "Failed", "message": "Missing required parameters."}

    # If only name is provided, fetch the Sales Order
    if not sales_order and name:
        sales_order = frappe.get_doc(doc_name, name)

    # If there's still no sales_order at this point, return failure
    if not sales_order:
        return {"status": "Failed", "message": "Unable to fetch Sales Order."}

    # Check if the specified email template exists
    if frappe.db.exists("Email Template", "invoice-email-template"):
        email_template = frappe.get_doc("Email Template", "invoice-email-template")
    else:
        default_email_templates = frappe.get_all("Email Template", limit=1)
        if not default_email_templates:
            return {"status": "Failed", "message": "No email template found."}
        email_template = frappe.get_doc("Email Template", default_email_templates[0].name)





    # Set the email recipients, fetching from the Sales Order customer's details
    # recipients = [sales_order.recipient_email]  # Assuming 'email_id' is the field in Sales Order for customer's email
    # Set the email recipients
    if not recipients:
        recipients = [sales_order.recipient_email]  # Assuming 'recipient_email' is the field in Sales Order for customer's email


    # Conditionally generate PDF of the Sales Order
    attachment_data = []
    if attachment:
        pdf_data = frappe.attach_print(doctype=doc_name, name=sales_order.name, file_name=F"{sales_order.name}-invoice.pdf" , print_letterhead=True)
        attachment_data.append(pdf_data)

    # Send email
    frappe.sendmail(
        recipients=recipients,
        subject=email_template.subject,
        message=email_template.response,
        attachments=attachment_data,
        reference_doctype=sales_order.doctype,
        reference_name=sales_order.name
    )

    return {"status": "Success", "message": "Email sent successfully."}


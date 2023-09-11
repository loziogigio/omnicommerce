import frappe
from frappe import _
from omnicommerce.controllers.pdf import get_pdf_data
from omnicommerce.controllers.pdf import get_default_letterhead

@frappe.whitelist(allow_guest=True)
def send_sales_order_confirmation_email(sales_order=None, name=None , attachment=True , recipients=None , email_template="confirm-sales-order" , wire_info=""):
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
    if frappe.db.exists("Email Template", email_template):
        email_template = frappe.get_doc("Email Template", email_template)
    else:
        default_email_templates = frappe.get_all("Email Template", limit=1)
        if not default_email_templates:
            return {"status": "Failed", "message": "No email template found."}
        email_template = frappe.get_doc("Email Template", default_email_templates[0].name)
        
    if not recipients:
        recipients = [sales_order.recipient_email]  # Assuming 'recipient_email' is the field in Sales Order for customer's email

    
    context = {
        **sales_order.as_dict(),
        "wire_info":wire_info
        # ... you can add other context variables as needed
    }
    try:
        # Render the email content with the context
        rendered_email_content = frappe.render_template(email_template.response, context)
        rendered_subject = frappe.render_template(email_template.subject, context)


        # Conditionally generate PDF of the Sales Order
        attachment_data = []
        if attachment:
            pdf_data = frappe.attach_print(doctype=doc_name, name=sales_order.name, file_name=F"{sales_order.name}-invoice.pdf" , print_letterhead=True)
            attachment_data.append(pdf_data)

        # Send email
        frappe.sendmail(
            recipients=recipients,
            subject=rendered_subject,
            message=rendered_email_content,
            attachments=attachment_data,
            reference_doctype=sales_order.doctype,
            reference_name=sales_order.name
        )

        return {"status": "Success", "message": "Email sent successfully."}
    except Exception as e:
        # Log the error
        frappe.log_error(message=f"Error sending sales order confirmation email for {sales_order.name}: {str(e)}", title=f"Sales Order {sales_order.name} Email Error ")

        # Return a response indicating that there was an error
        return {"status": "Failed", "message": f"Error encountered: {str(e)}"}


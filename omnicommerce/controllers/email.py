import frappe
from frappe import _
from omnicommerce.controllers.pdf import get_pdf_data
from omnicommerce.controllers.pdf import get_default_letterhead
from frappe.utils.file_manager import save_file


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



from frappe.utils.file_manager import save_file

@frappe.whitelist(allow_guest=True)
def request_form(**kwargs):

    # Extract form data from the request
    form_data = dict(frappe.request.form)
    
    # Merge form_data into kwargs. This will allow form fields to override any matching kwargs, if necessary.
    kwargs.update(form_data)
    
    request_id = kwargs.get('request_id', '')

    email_template="request-form"

    # Check if the specified email template exists
    if frappe.db.exists("Email Template", email_template):
        email_template = frappe.get_doc("Email Template", email_template)
    else:
        default_email_templates = frappe.get_all("Email Template", limit=1)
        if not default_email_templates:
            return {"status": "Failed", "message": "No email template found."}
        email_template = frappe.get_doc("Email Template", default_email_templates[0].name)

    # Handle attachment data
    attachments_to_send = []
    if hasattr(frappe.request, 'files') and frappe.request.files:
        for file_key in frappe.request.files:
            uploaded_file = frappe.request.files[file_key]
            
            file_content = uploaded_file.stream.read()  # Read the content from the stream

            file_data = save_file(
                fname=uploaded_file.filename,
                content=file_content,  # passing the content as bytes
                dt="Email Template",
                dn=email_template.name,  
                is_private=0
            )

            attachments_to_send.append({
                "fname": file_data.file_name,
                "fcontent": file_content  # You may need to base64 encode this if the email sending function expects it
            })
    else:
        attachments_to_send = None

    # Spread kwargs into context and replace underscores with spaces
    query_args = {key.replace('_', ' '): value for key, value in kwargs.items() if key not in ('cmd')}
    # This is your string representation
    context_string = ''
    if query_args:
        context_string += '<br/>'.join([f'{key}={value}' for key, value in query_args.items()]) + '<br/>'
        
    recipient = kwargs.get('recipient', '')
    
    recipients = [recipient]

    context = {
        "context":context_string,
        "request_id":request_id
        # ... you can add other context variables as needed
    }
    try:
        # Render the email content with the context
        rendered_email_content = frappe.render_template(email_template.response, context)
        rendered_subject = frappe.render_template(email_template.subject, context)

        # Send email
        frappe.sendmail(
            recipients=recipients,
            subject=rendered_subject,
            message=rendered_email_content,
            attachments=attachments_to_send
        )

        # Optionally, you can delete the saved files after sending the email if you no longer need them.
        for file_data.file_url in attachments_to_send:
            file_doc = frappe.get_doc("File", {"file_url": file_data.file_url})
            file_doc.flags.ignore_permissions = True
            file_doc.delete()

        return {"status": "Success", "message": "Email sent successfully."}
    except Exception as e:
        # Log the error
        frappe.log_error(message=f"Error sending sales order confirmation email for {context}: {str(e)}", title=f"Request Form  Email Error ")

        # Return a response indicating that there was an error
        return {"status": "Failed", "message": f"Error encountered: {str(e)}"}

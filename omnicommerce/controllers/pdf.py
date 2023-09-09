

import frappe
from payments.utils.utils import get_payment_gateway_controller
from mymb_ecommerce.utils.JWTManager import JWTManager, JWT_SECRET_KEY
jwt_manager = JWTManager(secret_key=JWT_SECRET_KEY)
from bs4 import BeautifulSoup
import os
from frappe.utils.pdf import get_pdf
from datetime import datetime
from frappe.utils.file_manager import save_file_on_filesystem





@frappe.whitelist(allow_guest=True)
@JWTManager.jwt_required
def get_sales_order_invoice(order_id):
    # Fetch the Sales Order using the provided order ID
    attached_to_doctype = "Sales Order"

    sales_order = frappe.get_doc(attached_to_doctype, order_id)
    # Return an error message if the Sales Order is not found
    if not sales_order:
        return {"error": f"No Sales Order found with ID {order_id}"}
    
    # Commented out the user check as you might want to adjust or implement it later
    # user = frappe.local.jwt_payload['email']
    # # Verify that the current user is the owner of the Sales Order
    # if not user == sales_order.customer:
    #     return {"error": "You do not have permission to access this Sales Order"}

    base_url = frappe.utils.get_url()
    # Define the desired file path structure
    file_path_structure = f"Home/Invoices/{sales_order.creation.year}/{sales_order.creation.month}"

    # Check if the file already exists
    existing_file = frappe.db.exists("File", {"file_name": f"{sales_order.name}.pdf", "attached_to_doctype": attached_to_doctype})
    if existing_file:
        file_doc = frappe.get_doc("File", existing_file)
        formatted_date = file_doc.creation.strftime("%d-%m-%Y")
        return {
            "name": sales_order.name,
            "attachment_files": [f"{base_url}{file_doc.file_url}"],
            "creation_date": formatted_date,
            "status": sales_order.status,
            "total": sales_order.total,
            "items": [{"item_code": item.item_code, "item_name": item.item_name, "qty": item.qty, "rate": item.rate, "image": item.image} for item in sales_order.items]
        }

    # Generate PDF data
    pdf_data = get_pdf_data(attached_to_doctype, sales_order.name, print_format="Standard", letterhead=get_default_letterhead())

    # Attach PDF to the Sales Order
    file_doc = save_and_attach(pdf_data, attached_to_doctype, sales_order.name, file_path_structure)
    formatted_date = file_doc.creation.strftime("%d-%m-%Y")

    # Extract the relevant fields from the Sales Order document and return them as a dictionary
    return {
        "name": sales_order.name,
        "attachment_files": [f"{base_url}{file_doc.file_url}"],
        "creation_date": formatted_date,
        "status": sales_order.status,
        "total": sales_order.total,
        "items": [{"item_code": item.item_code, "item_name": item.item_name, "qty": item.qty, "rate": item.rate, "image": item.image} for item in sales_order.items]
    }

def save_and_attach(content, to_doctype, to_name, folder):
    """
    Save content to disk and create a File document.

    File document is linked to another document.
    """
    file_name = "{to_name}.pdf".format(to_name=to_name.replace("/", "-"))

    # Check if folder exists, if not create it
    create_folder_structure(folder)


    file = frappe.new_doc("File")
    file.file_name = file_name
    file.content = content
    file.folder = folder
    file.is_private = 1
    file.attached_to_doctype = to_doctype
    file.attached_to_name = to_name
    file.save()
    frappe.db.commit() 

    return file



def create_folder_structure(folder_path):
    """Create a folder structure if it doesn't exist."""
    folders = folder_path.strip("/").split("/")
    
    # Ensure the first folder is always "Home", and avoid recreating it.
    if folders[0] == "Home":
        folders.pop(0)
    
    parent_folder = "Home"
    
    for folder in folders:
        current_folder_path = f"{parent_folder}/{folder}"
        
        # Check if current folder exists
        if not frappe.db.exists("File", {"file_name": folder, "is_folder": 1, "folder": parent_folder}):
            new_folder = frappe.new_doc("File")
            new_folder.file_name = folder
            new_folder.is_folder = 1
            new_folder.folder = parent_folder
            new_folder.insert()  # Insert the folder
            frappe.db.commit() 
            
        # Set the parent_folder for next iteration
        parent_folder = current_folder_path



def get_pdf_data(doctype, name, print_format=None, letterhead=None):
    """Document -> HTML -> PDF."""
    # html = frappe.get_print(doctype, name, print_format, letterhead=letterhead)

    # Define the cart as a dictionary
    cart = {
        'Samsung Galaxy S20': 10,
        'iPhone 13': 80
    }

    html = '<h1>Invoice from Star Electronics e-Store!</h1>'

    # Add items to PDF HTML
    html += '<ol>'
    for item, qty in cart.items():
        html += f'<li>{item} - {qty}</li>'
    html += '</ol>'
    

    return get_pdf(html)


def get_default_letterhead():

    # Fetch the default Letter Head
    default_letterhead = frappe.db.get_value('Letter Head', {'is_default': 1}, 'name')
    if not default_letterhead:
        frappe.throw(_("Please set a default Letter Head in Letter Head master."))
    return default_letterhead
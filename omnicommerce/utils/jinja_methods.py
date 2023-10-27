import json
import frappe
from frappe import db
from frappe.model.document import BaseDocument

def json_encode(data):
    if isinstance(data, BaseDocument):
        data = data.as_dict()
    return json.dumps(data, default=str, indent=4)

def translate(label, language):
    translations = {
        "Image": {
            "en": "Image",
            "es": "Imagen",
            "it": "Immagine",
            "sk": "Obrázok",
            "cz": "Obrázek"
        },
        "Item": {
            "en": "Item",
            "es": "Artículo",
            "it": "Articolo",
            "sk": "Položka",
            "cz": "Položka"
        },
        "Rate": {
            "en": "Rate",
            "es": "Tarifa",
            "it": "Prezzo",
            "sk": "Sadzba",
            "cz": "Sazba"
        },
        "Quantity": {
            "en": "Quantity",
            "es": "Cantidad",
            "it": "Quantità",
            "sk": "Množstvo",
            "cz": "Množství"
        },
        "Amount": {
            "en": "Valore",
            "es": "Monto",
            "it": "Importo",
            "sk": "Množstvo",
            "cz": "Částka"
        },
        "Discount": {
            "en": "Discount",
            "es": "Squento",
            "it": "Sconto",
            "sk": "Zľava",
            "cz": "Zľava"
        },
        "Net Price": {
            "en": "Net Price",
            "es": "Prezzo Netto",
            "it": "Prezzo Netto",
            "sk": "Cena",
            "cz": "Cena"
        },
        "%VAT": {
            "en": "%VAT",
            "es": "%IVA",
            "it": "%IVA",
            "sk": "%DPH",
            "cz": "%DPH"
        },
        "VAT": {
            "en": "VAT",
            "es": "IVA",
            "it": "IVA",
            "sk": "DPH",
            "cz": "DPH"
        },
        "EUR Total": {
            "en": "EUR Total",
            "es": "EUR Total",
            "it": "EUR Totale",
            "sk": "EUR Celkom",
            "cz": "EUR Celkom"
        }
    }

    return translations.get(label, {}).get(language, label)

@frappe.whitelist(allow_guest=True, methods=['POST'])
def generate_item_table_from_sales_invoice(sales_invoice_name , language="en"):
    # Fetch linked Sales Orders from the Sales Invoice items
    sales_orders = frappe.db.sql("""
        SELECT DISTINCT sales_order
        FROM `tabSales Invoice Item`
        WHERE parent = %s AND sales_order IS NOT NULL AND sales_order != ''
    """, (sales_invoice_name,), as_dict=True)

    # Extract Sales Order names
    sales_order_names = [entry.sales_order for entry in sales_orders]
    
    if not sales_order_names:
        return {"error": "No associated Sales Order found for this Invoice."}

    return generate_item_table(sales_order_name=sales_order_names[0] , language=language)


@frappe.whitelist(allow_guest=True, methods=['POST'])
def generate_item_table( sales_order_name=None , language="en", items=None):
    if sales_order_name:
        items = db.get_values("Sales Order Item", filters={"parent": sales_order_name}, fieldname=["image", "item_code", "item_name", "rate", "qty", "amount", "net_rate" , "net_amount", "discount_percentage", "discount_amount"], as_dict=True)
        taxes = get_sales_order_taxes(sales_order_name)
        cumulative_tax_rate = sum([tax.rate for tax in taxes])
        vat_percent = int(cumulative_tax_rate)
        total_sales_order_discount = frappe.db.get_value("Sales Order", sales_order_name, "discount_amount") or 0
    
    table_html = f"""<table border="1" style="width: 100%; border-collapse: collapse;">
        <thead>
            <tr border="1">
                <th style="width:50%;text-align:left;border: 1px solid black;padding: 5px;">{translate("Item", language)}</th>
                <th style="text-align:center;border: 1px solid black">{translate("Quantity", language)}</th>
                <th style="text-align:center;border: 1px solid black">{translate("Rate", language)}</th>
                <th style="text-align:center;border: 1px solid black">{translate("Discount", language)}</th>
                <th style="text-align:center;border: 1px solid black">{translate("Net Price", language)}</th>
                <th style="text-align:center;border: 1px solid black">{translate("%VAT", language)}</th>
                <th style="text-align:center;border: 1px solid black">{translate("VAT", language)}</th>
                <th style="text-align:center;border: 1px solid black">{translate("EUR Total", language)}</th>
            </tr>
        </thead>
        <tbody style="border: 1px solid black;">"""


    for item in items:
        item_tax = calculate_item_tax(item.rate, taxes) if sales_order_name else 0
        amount_tax = item_tax*item.get('qty')

        if all(not tax.get('included_in_print_rate') for tax in taxes):  # If no tax is included in print rate
            net_rate = item.get("net_rate") 
            rate = item.get("rate") + item_tax
            amount = rate*item.get('qty')
            

        else:
            net_rate = item.get("net_rate") 
            rate = item.get("rate") 
            amount = rate*item.get('qty')

        row_html = f"""
            <tr>
                <td style="text-align:left;padding: 5px;">{item.get('item_code')} : {item.get('item_name')}</td>
                <td style="text-align:center;">{item.get('qty')}</td>
                <td style="text-align:center;">{'%.2f' % rate}</td>
                <td style="text-align:center;">{'%.2f' % item.get('discount_amount', 0)}</td>
                <td style="text-align:center;">{'%.2f' % net_rate}</td>
                <td style="text-align:center;">{vat_percent}</td>
                <td style="text-align:center;">{'%.2f' % amount_tax}</td>
                <td style="text-align:center;">{'%.2f' % amount}</td>
            </tr>
        """

        table_html += row_html

    discount_net_amount = total_sales_order_discount / (1 + (vat_percent/100))
    discount_vat_amount = total_sales_order_discount - discount_net_amount
    discount_qty = 1 if discount_net_amount > 0 else 0


    discount_row = f"""
        <tr>
            <td style="text-align:left;padding: 5px;" >{translate("Discount", language)}</td>
            <td style="text-align:center;">{discount_qty}</td>
            <td style="text-align:center;" >{'%.2f' % total_sales_order_discount}</td>
            <td style="text-align:center;"></td>
            <td style="text-align:center;">{'%.2f' % discount_net_amount}</td>
            <td style="text-align:center;" >{vat_percent}</td>
            <td style="text-align:center;" >{'%.2f' % discount_vat_amount}</td>
            <td style="text-align:center;" >{'%.2f' % total_sales_order_discount}</td>

        </tr>
        """

    table_html += discount_row+"</tbody></table>"

    return table_html

def get_sales_order_taxes(sales_order_name):
    return db.get_all("Sales Taxes and Charges", filters={"parent": sales_order_name}, fields=["rate", "included_in_print_rate"])


def calculate_item_tax(item_amount, taxes):
    total_tax = 0
    for tax in taxes:
        if tax.get('included_in_print_rate'):
            # Tax is already included in the item rate, so we reverse calculate
            tax_amount = (item_amount * tax.get('rate')) / (100 + tax.get('rate'))
        else:
            # Tax is on top of the item rate
            tax_amount = (item_amount * tax.get('rate')) / 100
        
        total_tax += tax_amount
    
    return total_tax

def customer_info_box(sales_order, language="en"):
    # Translations dictionary
    translations = {
        "Customer Info": {
            "en": "Customer Info",
            "es": "Información del Cliente",
            "it": "Spett.le",
            "sk": "Informácie o Zákazníkovi",
            "cz": "Informace o Zákazníkovi"
        },
        "Name": {
            "en": "Name",
            "es": "Nombre",
            "it": "Nome",
            "sk": "Meno",
            "cz": "Jméno"
        },
        "Company Name": {
            "en": "Company Name",
            "es": "Nombre de la Empresa",
            "it": "Ragione sociale",
            "sk": "Názov Spoločnosti",
            "cz": "Název Společnosti"
        },
        "VAT Number": {
            "en": "VAT Number",
            "es": "Número de IVA",
            "it": "Partita IVA",
            "sk": "IČ DPH",
            "cz": "DIČ"
        },
        "TAX Code": {
            "en": "TAX Code",
            "es": "Número de IVA",
            "it": "Codice Fiscale/P.IVA",
            "sk": "IČ DPH",
            "cz": "DIČ"
        }
    }
    
    # Extract translated labels
    translated_label = translations["Customer Info"].get(language, "Customer Info")
    translated_name = translations["Name"].get(language, "Name")
    translated_company_name = translations["Company Name"].get(language, "Company Name")
    translated_vat_number = translations["VAT Number"].get(language, "VAT Number")
    translated_tax_code = translations["TAX Code"].get(language, "TAX Code")
    
    # Construct the info box with only valued attributes
    info_html = f"""
    <div style="border: 1px solid black; padding: 10px; width: 100%; margin: 10px 0;border-radius:5px">
        <div style="border-bottom: 1px solid black; padding-bottom: 5px;border-radius:0px">
            <strong>{translated_label}</strong>
        </div>
        <div>
            <strong>{translated_name}:</strong> {sales_order.customer_name}<br>"""
    
    if sales_order.recipient_email:
        info_html += f"""<strong>Email:</strong> {sales_order.recipient_email}<br>"""
    if sales_order.customer_type == 'Company' and sales_order.company_name:
        info_html += f"""<strong>{translated_company_name}:</strong> {sales_order.company_name}<br>"""
    if sales_order.vat_number:
        info_html += f"""<strong>{translated_vat_number}:</strong> {sales_order.vat_number}<br>"""
    if sales_order.pec:
        info_html += f"""<strong>Pec:</strong> {sales_order.pec}<br>"""
    if sales_order.recipient_code:
        info_html += f"""<strong>SDI:</strong> {sales_order.recipient_code}<br>"""
    if sales_order.tax_code:
        info_html += f"""<strong>{translated_tax_code}:</strong> {sales_order.tax_code}<br>"""

    info_html += """
        </div>
    </div>
    """

    return info_html



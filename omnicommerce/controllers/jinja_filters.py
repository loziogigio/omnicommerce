import json
import frappe
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
        }
    }
    
    return translations.get(label, {}).get(language, label)

def generate_item_table(items, language="en"):
    table_html = f"""<table border="1" style="width: 100%; border-collapse: collapse;">
        <thead>
            <tr border="1">
                <th style="padding: 5px;">{translate("Image", language)}</th>
                <th style="padding: 5px;">{translate("Item", language)}</th>
                <th style="padding: 5px;">{translate("Rate", language)}</th>
                <th style="padding: 5px;">{translate("Quantity", language)}</th>
                <th style="padding: 5px;">{translate("Amount", language)}</th>
            </tr>
        </thead>
        <tbody>"""

    for item in items:
        row_html = f"""
            <tr>
                <td><img src="{item.image}" alt="{item.item_code}" style="width:50px"></td>
                <td>{item.item_code} : {item.item_name}</td>
                <td>{item.rate}</td>
                <td>{item.qty}</td>
                <td>{item.amount}</td>
            </tr>
        """
        table_html += row_html

    table_html += "</tbody></table>"

    return table_html



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




import frappe
from frappe.model.db_query import DatabaseQuery
from omnicommerce.controllers.solr_crud import add_document_to_solr
from datetime import datetime
from erpnext.e_commerce.shopping_cart.product_info import get_product_info_for_website
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from bs4 import BeautifulSoup

config = Configurations()
solr_instance = config.get_solr_instance()
image_uri_instance = config.get_image_uri_instance()

@frappe.whitelist(allow_guest=True, methods=['POST'])
def get_website_items(limit=None, page=1, filters=None):
    try:

        # Get the meta object for the "Website Item" DocType
        meta = frappe.get_meta("Website Item")
        field_keys = [field.fieldname for field in meta.fields]
        field_keys.append('name') # Consider 'name' as a valid key

        # Create a new dictionary with only the valid keys and values from the filters
        valid_filters = {key: value for key, value in filters.items() if key in field_keys}
         # Collect any non-valid keys
        non_valid_keys = [key for key in filters.keys() if key not in field_keys]
        warning_message = ''
        if non_valid_keys:
            warning_message = f"Warning: The following filter keys were ignored as they are not valid: {', '.join(non_valid_keys)}."



        start = (page - 1) * int(limit) if limit else 0

        filtered_website_items = frappe.get_all("Website Item", fields=["*"], filters=valid_filters, limit=limit, start=start)
        
        items_data = []
        for website_item in filtered_website_items:
            product = get_product_info_for_website(item_code=website_item.item_code , skip_quotation_creation=True)
            merged_data = {
                **website_item,
                **product,

            }
            slideshow_items = None

            if website_item.slideshow:
                slideshow_items = get_slideshow_for_website(website_item.slideshow)
            if slideshow_items:
                merged_data['slideshow_items'] = slideshow_items # Include slideshow details only if exists

            items_data.append(merged_data)


        result = {
            "data": items_data,
            "count": len(items_data)
        }
        
        # Add warning to result if warning_message is not empty
        if warning_message:
            result["warning"] = warning_message

        return result


    except Exception as e:
        frappe.log_error(message=f"An unexpected error occurred: {str(e)}", title="Unexpected Error in get_website_items")
        return {
            "error": f"An unexpected error occurred. {str(e)}",
            "data": [],
            "count": 0
        }


def get_slideshow_for_website(slideshow_name):
    try:
        # Try to get the slideshow details based on the given slideshow_name
        slideshow_items = frappe.db.get_all("Website Slideshow Item", filters={"parent": slideshow_name}, order_by="idx" , fields=["*"])
        return slideshow_items
    except frappe.DoesNotExistError:
        # Handle the case when the slideshow does not exist
        return None

@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_website_items_in_solr(limit=None, page=None, filters=None):
    items = get_website_items(limit=limit, page=page, filters=filters)

    success_items = []
    failure_items = []
    skipped_items = []

    for item in items["data"]:
        solr_document = transform_to_solr_document(item)

        # if solr_document is None or not item['data'].get('name') or not item['data'].get('website_image'):
        #     sku = item['data'].get('item_code', "No code available")
        #     skipped_items.append(sku)
        #     solr_id = solr_document['id'] if solr_document else "No id available"
        #     frappe.log_error(f"Warning: Skipped Item in solr  SKU: {sku} , D: {solr_id}  to Solr", f"Skipped document with SKU: {sku} due to missing slug or prices or properties or medias. {solr_document}")
        #     continue

        result = add_document_to_solr(solr_document)
        if result['status'] == 'success':
            success_items.append(solr_document['sku'])
        else:
            failure_items.append(solr_document['sku'])
            frappe.log_error(title=f"Error: Import Item in solr SKU: {solr_document['sku']} ID: {solr_document['id']} ", message=f"Failed to add document with SKU: {solr_document['sku']} to Solr. Reason: {result['reason']}")

    return {
        "data": {
            "success_items": success_items,
            "failure_items": failure_items,
            "skipped_items": skipped_items,
            "summary": {
                "success": len(success_items),
                "failure": len(failure_items),
                "skipped": len(skipped_items)
            }
        }
    }


def transform_to_solr_document(item):
    

    id =  item['item_code']
    sku = item['item_code']
    
    name = item['web_item_name'] or item['item_name']
    name = BeautifulSoup(name, 'html.parser').get_text() if name else None

    slug = item['route']
    # If slug is None, return None to skip this item
    # if slug is None or prices is None or id is None or sku is None:
    #     return None
    
    short_description = item['short_description']
    short_description = BeautifulSoup(short_description, 'html.parser').get_text() if short_description else None
    description = item['web_long_description']
    description = BeautifulSoup(description, 'html.parser').get_text() if description else None

    brand = item['brand']
    if item['website_image']:
        images = item['website_image']
    if item['slideshow_items']:
        images = [item['image'] for item in item['slideshow_items']]


    
    prices = item['product_info']['price']

    net_price = prices['price_list_rate']
    net_price_with_vat = prices.get('net_price_with_vat', net_price)
    gross_price = prices.get('gross_price', net_price)
    gross_price_with_vat = prices.get('gross_price_with_vat', net_price)
    availability = item['product_info']['stock_qty'][0][0]
    is_promo = prices.get('is_promo', False)
    is_best_promo = prices.get('is_best_promo', False)
    promo_price = prices.get('promo_price', 0)
    promo_price_with_vat = prices.get('promo_price_with_vat', 0)

    discount_value = discount_percent = None
    if is_promo and gross_price_with_vat:
        discount_value = round(gross_price_with_vat - promo_price_with_vat,2)
        discount_percent= int((1 - promo_price_with_vat/gross_price_with_vat)*100) if gross_price_with_vat else None
        
    start_promo_date_str = prices.get('start_promo_date', None)
    end_promo_date_str = prices.get('end_promo_date', None)
    # Transform date strings to Solr date format if they are not None
    start_promo_date = datetime.strptime(start_promo_date_str, "%d/%m/%y").strftime("%Y-%m-%dT%H:%M:%SZ") if start_promo_date_str else None
    end_promo_date = datetime.strptime(end_promo_date_str, "%d/%m/%y").strftime("%Y-%m-%dT%H:%M:%SZ") if end_promo_date_str else None
    
    solr_document = {
        "id": id,
        "sku": sku,
        "availability": availability,
        "name": name,
        "name_nostem": name,
        "short_description": short_description,
        "short_description_nostem": short_description,
        "description": description,
        "description_nostem": description,
        "sku_father": item.get('sku_father', None),
        "num_images": len(images),
        "images": images,
        "id_brand": item.get('id_brand', []),
        "id_father": item.get('id_father', None),
        "keywords": item.get('keywords', None),
        "model": item.get('model', None),
        "model_nostem": item.get('model_nostem', None),
        "discount_value":discount_value,
        "discount_percent":discount_percent,
        "slug": slug,
        "synonymous": item.get('synonymous', None),
        "synonymous_nostem": item.get('synonymous_nostem', None),
        "gross_price": gross_price,
        "gross_price_with_vat": gross_price_with_vat,
        "net_price": net_price,
        "net_price_with_vat":net_price_with_vat ,
        "promo_code": prices.get('promo_code', None),
        "promo_price": promo_price,
        "promo_price_with_vat": promo_price_with_vat,
        "is_promo": is_promo,
        "is_best_promo": is_best_promo,
        "promo_title": prices.get('promo_title', None),
        "start_promo_date": start_promo_date,
        "end_promo_date": end_promo_date,
        "discount": prices.get('discount', [None]*6),
        "discount_extra": prices.get('discount_extra', [None]*3),
        "pricelist_type": prices.get('pricelist_type', None),
        "pricelist_code": prices.get('pricelist_code', None)
    }

    return solr_document

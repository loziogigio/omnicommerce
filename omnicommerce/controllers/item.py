import frappe
from frappe.model.db_query import DatabaseQuery
from frappe.utils.password import update_password
from omnicommerce.controllers.solr_crud import add_document_to_solr
from slugify import slugify
from datetime import datetime
from omnicommerce.utils.Media import Media
from omnicommerce.utils.htmlParser import parseHtmlText
from erpnext.utilities.product import get_price, get_web_item_qty_in_stock
from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import (
	get_shopping_cart_settings,
)
from mymb_ecommerce.mymb_b2c.settings.configurations import Configurations
from erpnext.e_commerce.shopping_cart.cart import _get_cart_quotation, _set_price_list


config = Configurations()
solr_instance = config.get_solr_instance()
image_uri_instance = config.get_image_uri_instance()

@frappe.whitelist(allow_guest=True, methods=['POST'])
def get_website_items(limit=None, page=1, filters=None, skip_quotation_creation=False):
    try:
        # Get the meta object for the "Website Item" DocType
        meta = frappe.get_meta("Website Item")
        field_keys = [field.fieldname for field in meta.fields]

        # Validate the keys in the filters against the field names in the DocType
        for key in filters.keys():
            if key not in field_keys:
                return {
                    "error": f"Invalid filter key: {key}.",
                    "data": [],
                    "count": 0
                }

        start = (page - 1) * int(limit) if limit else 0

        filtered_website_items = frappe.get_all("Website Item", fields=["*"], filters=filters, limit=limit, start=start)
        
        items_data = []
        for website_item in filtered_website_items:
            uom = website_item.get("stock_uom")
            sku = website_item.get("item_code")
            slug = website_item.get("route")

            cart_settings = get_shopping_cart_settings()
            if not cart_settings.enabled:
                # return settings even if cart is disabled
                return frappe._dict({"product_info": {}, "cart_settings": cart_settings})

            cart_quotation = frappe._dict()
            if not skip_quotation_creation:
                cart_quotation = _get_cart_quotation()

            selling_price_list = (
                cart_quotation.get("selling_price_list")
                if cart_quotation
                else _set_price_list(cart_settings, None)
            )

            price = {}
            if cart_settings.show_price:
                is_guest = frappe.session.user == "Guest"
                # Show Price if logged in.
                # If not logged in, check if price is hidden for guest.
                if not is_guest or not cart_settings.hide_price_for_guest:
                    prices = get_price(
                        sku, selling_price_list, cart_settings.default_customer_group, cart_settings.company
                    )
                    stock_data = get_web_item_qty_in_stock(sku, "website_warehouse")
            
            website_item['uom'] = uom
            website_item['sku'] = sku
            website_item['slug'] = slug
            website_item['prices'] = prices
            website_item['stock_data'] = stock_data
            item_data = {
                "data": website_item,
            }
            items_data.append(item_data)

        return {
            "data": items_data,
            "count": len(items_data)
        }

    except Exception as e:
        frappe.log_error(message=f"An unexpected error occurred: {str(e)}", title="Unexpected Error in get_website_items")
        return {
            "error": "An unexpected error occurred. Please check the server logs for more details.",
            "data": [],
            "count": 0
        }



@frappe.whitelist(allow_guest=True, methods=['POST'])
def import_website_items_in_solr(limit=None, page=None, filters=None, skip_quotation_creation=False):
    items = get_website_items(limit=limit, page=page, filters=filters, skip_quotation_creation=skip_quotation_creation)

    success_items = []
    failure_items = []
    skipped_items = []

    for item in items["data"]:
        solr_document = transform_to_solr_document(item)

        if solr_document is None or not item['data'].get('name') or not item['data'].get('website_image'):
            sku = item['data'].get('item_code', "No code available")
            skipped_items.append(sku)
            solr_id = solr_document['id'] if solr_document else "No id available"
            frappe.log_error(f"Warning: Skipped Item in solr  SKU: {sku} , D: {solr_id}  to Solr", f"Skipped document with SKU: {sku} due to missing slug or prices or properties or medias. {solr_document}")
            continue

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
    solr_item=item['data']

    prices = solr_item.get('prices', None)
    stock_data = solr_item.get('stock_data', None)
    id =  solr_item.get('name', None)
    sku = solr_item.get('sku', None)
    name = parseHtmlText(solr_item.get('web_item_name', None))
    slug = solr_item.get('slug', None)
    short_description = parseHtmlText(solr_item.get('short_description', None))
    web_long_description = parseHtmlText(solr_item.get('web_long_description', None))
    description = parseHtmlText(solr_item.get('description', None))
    owner = solr_item.get('owner', None)
    release_date_obj = solr_item.get('modified', None)
    release_date = release_date_obj.strftime("%Y-%m-%dT%H:%M:%SZ") if release_date_obj else None
    ratings = solr_item.get('ranking', None)
    

    # Price Section
    net_price = prices.get('price_list_rate', 0)
    gross_price = prices.get('price_list_rate', 0)
    promo_price = prices.get('promo_price', 0)
    stock = stock_data.get("stock_qty", 0)
    in_stock = stock_data.get("in_stock", None)
    is_out_of_stock = in_stock == 0
    sale_count = stock_data.get('is_stock_item', 0)
    is_sale = sale_count > 0
    website_image = solr_item.get('website_image', None)
    media = Media(image_uri_instance)
    image_list = media.get_image_sizes({"images": [website_image]});


    # If slug is None, return None to skip this item
    if slug is None or prices is None or id is None or sku is None:
        return None
   
    solr_document = {
        "description": description,
        "developer": None,
        "gallery_pictures": image_list['gallery_pictures'],
        "game_mode": None,
        "gross_price": gross_price,
        "id": id,
        "is_hot" : False,
        "is_new" : False,
        "is_out_of_stock" : is_out_of_stock,
        "is_sale" : is_sale,
        "large_pictures" : image_list['large_pictures'],
        "long_description" : web_long_description,
        "main_pictures" : image_list['main_pictures'],
        "name": name,
        "net_price": net_price,
        "price": net_price,
        "promo_price": promo_price,
        "publisher" : owner,
        "rated": False, # todo
        "ratings": ratings,
        "release_date" :release_date, 
        "reviews" : [],
        "sale_count" : sale_count,
        "sale_price" : net_price,
        "short_description": short_description,
        "sku": sku,
        "slug": slug,
        "small_pictures" : image_list['small_pictures'],
        "stock" : stock,
        "until": None,
        "variants" : []
    }


    return solr_document

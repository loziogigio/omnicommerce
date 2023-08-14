import frappe
from datetime import datetime
from frappe.utils.password import update_password
from omnicommerce.controllers.solr_crud import add_document_to_solr
from bs4 import BeautifulSoup
from slugify import slugify
from datetime import datetime
from erpnext.utilities.product import get_price
from erpnext.e_commerce.doctype.e_commerce_settings.e_commerce_settings import (
	get_shopping_cart_settings,
	show_quantity_in_website,
)
from erpnext.e_commerce.shopping_cart.cart import _get_cart_quotation, _set_price_list


@frappe.whitelist(allow_guest=True, methods=['POST'])
def get_website_items(limit=None, page=1, filters=None, skip_quotation_creation=False):
    try:
        if filters is None or not isinstance(filters, dict):
            return {
                "error": "Invalid or missing filters.",
                "data": [],
                "count": 0
            }
        start = (page - 1) * int(limit) if limit else 0

        # Initial fetch of all Website Items without any conditions
        all_website_items = frappe.get_all("Website Item", fields=["*"], limit=limit, start=start)
        
        # Manually filtering based on the provided filters
        filtered_website_items = []
        for website_item in all_website_items:
            is_match = True
            for key, value in filters.items():
                if not hasattr(website_item, key) or getattr(website_item, key) != value:
                    is_match = False
                    break

            if is_match:
                filtered_website_items.append(website_item)


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
                    price = get_price(
                        sku, selling_price_list, cart_settings.default_customer_group, cart_settings.company
                    )
            
            website_item['uom'] = uom
            website_item['sku'] = sku
            website_item['slug'] = slug
            website_item['prices'] = price
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
    id =  solr_item.get('name', None)
    sku = solr_item.get('sku', None)
    name = solr_item.get('web_item_name', None)
    name = BeautifulSoup(name, 'html.parser').get_text() if name else None
    slug = solr_item.get('slug', None)
    # If slug is None, return None to skip this item
    if slug is None or prices is None or id is None or sku is None:
        return None
    
    short_description = solr_item.get('short_description', None)
    short_description = BeautifulSoup(short_description, 'html.parser').get_text() if short_description else None
    web_long_description = solr_item.get('web_long_description', None)
    web_long_description = BeautifulSoup(web_long_description, 'html.parser').get_text() if web_long_description else None
    description = solr_item.get('description', None)
    description = BeautifulSoup(description, 'html.parser').get_text() if description else None

    brand = solr_item.get('brand', None)
    slideshow = solr_item.get('slideshow', None)
    uom = solr_item.get('uom', None)
    stock_uom = solr_item.get('stock_uom', None)
    item_group = solr_item.get('item_group', None)
    published = solr_item.get('published', None)
    naming_series = solr_item.get('naming_series', None)
    thumbnail = [solr_item.get('thumbnail', None)]
    images = [solr_item.get('website_image', None)]
    creation = solr_item.get('creation', None)
    modified = solr_item.get('modified', None)
    modified_by = solr_item.get('modified_by', None)
    owner = solr_item.get('owner', None)
    docstatus = solr_item.get('docstatus', None)
    idx = solr_item.get('idx', None)
    has_variants = solr_item.get('has_variants', None)
    variant_of = solr_item.get('variant_of', None)
    website_warehouse = solr_item.get('website_warehouse', None)
    on_backorder = solr_item.get('on_backorder', None)
    show_tabbed_section = solr_item.get('show_tabbed_section', None)
    ranking = solr_item.get('ranking', None)
    website_content = solr_item.get('website_content', None)
    _user_tags = solr_item.get('_user_tags', None)
    _comments = solr_item.get('_comments', None)
    _assign = solr_item.get('_assign', None)
    _liked_by = solr_item.get('_liked_by', None)

    net_price = prices.get('net_price', 0)
    net_price_with_vat = prices.get('net_price_with_vat', 0)
    gross_price = prices.get('price_list_rate', 0)
    gross_price_with_vat = prices.get('gross_price_with_vat', 0)
    availability = prices.get('availability', 0)
    is_promo = prices.get('is_promo', False)
    is_best_promo = prices.get('is_best_promo', False)
    promo_price = prices.get('promo_price', 0)
    promo_price_with_vat = prices.get('promo_price_with_vat', 0)
    price_list_rate = prices.get('price_list_rate', 0)
    currency = prices.get('currency', 0)
    formatted_price = prices.get('formatted_price', 0)
    currency_symbol = prices.get('currency_symbol', 0)
    formatted_price_sales_uom = prices.get('formatted_price_sales_uom', 0)

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
        "price_list_rate": price_list_rate,
        "currency": currency,
        "formatted_price": formatted_price,
        "currency_symbol": currency_symbol,
        "formatted_price_sales_uom": formatted_price_sales_uom,
        "is_promo": is_promo,
        "is_best_promo": is_best_promo,
        "promo_title": prices.get('promo_title', None),
        "start_promo_date": start_promo_date,
        "end_promo_date": end_promo_date,
        "discount": prices.get('discount', [None]*6),
        "discount_extra": prices.get('discount_extra', [None]*3),
        "pricelist_type": prices.get('pricelist_type', None),
        "pricelist_code": prices.get('pricelist_code', None),
        "brand": brand,
        "slideshow": slideshow,
        "thumbnail": thumbnail,
        "uom": uom,
        "stock_uom": stock_uom,
        "item_group": item_group,
        "published": published,
        "naming_series": naming_series,
        "creation": creation,
        "modified": modified,
        "modified_by": modified_by,
        "owner": owner,
        "docstatus": docstatus,
        "idx": idx,
        "has_variants": has_variants,
        "variant_of": variant_of,
        "website_warehouse": website_warehouse,
        "on_backorder": on_backorder,
        "show_tabbed_section": show_tabbed_section,
        "ranking": ranking,
        "website_content": website_content,
        "_user_tags": _user_tags,
        "_comments": _comments,
        "_assign": _assign,
        "naming_series": naming_series,
        "_liked_by": _liked_by,

    }

    return solr_document

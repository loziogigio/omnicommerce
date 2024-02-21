import frappe


@frappe.whitelist(allow_guest=True, methods=['POST'])
def get_blog_post(limit=10, page=1, filters=None):
    try:

        # Get the meta object for the "Blog Post" DocType
        meta = frappe.get_meta("Blog Post")
        field_keys = [field.fieldname for field in meta.fields]
        field_keys.append('name') # Consider 'name' as a valid key

        if filters is None:
            filters = {}

        # Create a new dictionary with only the valid keys and values from the filters
        valid_filters = {key: value for key, value in filters.items() if key in field_keys}
         # Collect any non-valid keys
        non_valid_keys = [key for key in filters.keys() if key not in field_keys]
        warning_message = ''
        if non_valid_keys:
            warning_message = f"Warning: The following filter keys were ignored as they are not valid: {', '.join(non_valid_keys)}."



        start = (page - 1) * int(limit) if limit else 0

        filtered_blog_post = frappe.get_all("Blog Post", 
                                            fields=["*"], 
                                            filters=valid_filters, 
                                            limit=limit, 
                                            start=start,
                                            order_by='creation desc'  # or 'publish_date desc'
                                           )
        

        result = {
            "data": filtered_blog_post,
            "count": len(filtered_blog_post)
        }
        
        # Add warning to result if warning_message is not empty
        if warning_message:
            result["warning"] = warning_message

        return result

    except Exception as e:
        frappe.log_error(message=f"An unexpected error occurred: {str(e)}", title="Unexpected Error in get_blog_post")
        return {
            "error": f"An unexpected error occurred. {str(e)}",
            "data": [],
            "count": 0
        }
    
@frappe.whitelist(allow_guest=True, methods=['GET'])
def get_blog_post_detail(route=None):
    try:
        # Check if the route is provided
        if route is None:
            return {"error": "Route is a mandatory field."}

        # Get the blog post using the provided route
        blog_post = frappe.get_all("Blog Post", fields=["*"], filters={"route": route}, limit=1)

        # Check if a blog post was found
        if not blog_post:
            return {"error": "No blog post found for the given route."}

        result = {
            "data": blog_post[0],  # Return the first (and only) matching blog post
        }

        return result

    except Exception as e:
        frappe.log_error(message=f"An unexpected error occurred: {str(e)}", title="Unexpected Error in get_blog_post_detail")
        return {
            "error": f"An unexpected error occurred. {str(e)}"
        }
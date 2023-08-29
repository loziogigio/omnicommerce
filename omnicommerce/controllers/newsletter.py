import frappe
import frappe.utils
from frappe import _
from frappe.email.doctype.email_group.email_group import add_subscribers
from frappe.rate_limiter import rate_limit
from frappe.utils.verified_command import get_signed_params, verify_request


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60 * 60)
def subscribe(email, email_group=None):  # noqa
    """API endpoint to subscribe an email to a particular email group. Triggers a confirmation email."""

    if email_group is None:
        email_group = _("Website")
    
    # Get the b2c_url from the Mymb b2c Settings Doctype
    b2c_url = frappe.db.get_value("Mymb b2c Settings", "", "b2c_url")
    
    # build subscription confirmation URL
    api_endpoint = frappe.utils.get_url(
        f"{b2c_url}/pages/confirm_subscription?api=api/method/omnicommerce.controllers.newsletter.confirm_subscription"
    )
    signed_params = get_signed_params({"email": email, "email_group": email_group})
    confirm_subscription_url = f"{api_endpoint}&{signed_params}"

    # fetch custom template if available
    email_confirmation_template = frappe.db.get_value(
        "Email Group", email_group, "confirmation_email_template"
    )

    # build email and send
    if email_confirmation_template:
        args = {"email": email, "confirmation_url": confirm_subscription_url, "email_group": email_group}
        email_template = frappe.get_doc("Email Template", email_confirmation_template)
        email_subject = email_template.subject
        content = frappe.render_template(email_template.response, args)
    else:
        email_subject = _("Confirm Your Email")
        translatable_content = (
            _("Thank you for your interest in subscribing to our updates"),
            _("Please verify your Email Address"),
            confirm_subscription_url,
            _("Click here to verify"),
        )
        content = """
            <p>{}. {}.</p>
            <p><a href="{}">{}</a></p>
        """.format(
            *translatable_content
        )

    frappe.sendmail(
        email,
        subject=email_subject,
        content=content,
    )

    return {
        "status": "success",
        "message": _("Thank you for subscribing! Please check your email to confirm your subscription.")
    }


@frappe.whitelist(allow_guest=True)
def confirm_subscription(email, email_group=_("Website")):  # noqa
	"""API endpoint to confirm email subscription.
	This endpoint is called when user clicks on the link sent to their mail.
	"""
	if not verify_request():
		return {"status": "error", "message": _("Invalid Request")}

	if not frappe.db.exists("Email Group", email_group):
		frappe.get_doc({"doctype": "Email Group", "title": email_group}).insert(ignore_permissions=True)

	frappe.flags.ignore_permissions = True

	add_subscribers(email_group, email)
	frappe.db.commit()

	return {
		"status": "success",
		"message": _("{0} has been successfully added to the Email Group.").format(email)
	}


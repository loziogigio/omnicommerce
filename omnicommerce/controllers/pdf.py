"""

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import frappe
from frappe import _
from frappe.core.api.file import create_new_folder
from frappe.model.naming import _format_autoname
from frappe.realtime import publish_realtime
from frappe.utils.weasyprint import PrintFormatGenerator



def attach_pdf(doctype, name, title, lang=None, auto_name=None, print_format=None, letterhead=None):
    """
    Queue calls this method, when it's ready.

    1. Create necessary folders
    2. Get raw PDF data
    3. Save PDF file and attach it to the document
    """


    if lang:
        frappe.local.lang = lang
        # unset lang and jenv to load new language
        frappe.local.lang_full_dict = None
        frappe.local.jenv = None



    doctype_folder = "Home/" + doctype
    title_folder = doctype_folder + "/" + title




    if frappe.db.get_value("Print Format", print_format, "print_format_builder_beta"):
        doc = frappe.get_doc(doctype, name)
        pdf_data = PrintFormatGenerator(print_format, doc, letterhead).render_pdf()
    else:
        pdf_data = get_pdf_data(doctype, name, print_format, letterhead)



    return save_and_attach(pdf_data, doctype, name, title_folder, auto_name)



def create_folder(folder, parent):
    """Make sure the folder exists and return it's name."""
    new_folder_name = "/".join([parent, folder])
    
    if not frappe.db.exists("File", new_folder_name):
        create_new_folder(folder, parent)
    
    return new_folder_name


def get_pdf_data(doctype, name, print_format: None, letterhead: None):
    """Document -> HTML -> PDF."""
    html = frappe.get_print(doctype, name, print_format, letterhead=letterhead)
    return frappe.utils.pdf.get_pdf(html)


def save_and_attach(content, to_doctype, to_name, folder, auto_name=None):
    """
    Save content to disk and create a File document.

    File document is linked to another document.
    """
    if auto_name:
        doc = frappe.get_doc(to_doctype, to_name)
        # based on type of format used set_name_form_naming_option return result.
        pdf_name = set_name_from_naming_options(auto_name, doc)
        file_name = "{pdf_name}.pdf".format(pdf_name=pdf_name.replace("/", "-"))
    else:
        file_name = "{to_name}.pdf".format(to_name=to_name.replace("/", "-"))

    file = frappe.new_doc("File")
    file.file_name = file_name
    file.content = content
    file.folder = folder
    file.is_private = 0
    file.attached_to_doctype = to_doctype
    file.attached_to_name = to_name
    file.save()
    return file


def set_name_from_naming_options(autoname, doc):
    """
    Get a name based on the autoname field option
    """
    _autoname = autoname.lower()

    if _autoname.startswith("format:"):
        return _format_autoname(autoname, doc)

    return doc.name

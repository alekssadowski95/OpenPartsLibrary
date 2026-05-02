try:
    from flask_admin import Admin
    from flask_admin.contrib.sqla import ModelView
except ImportError:
    Admin = None
    ModelView = None

from openpartslibrary.models import Component, ComponentComponent, DownloadEvent, File, Material, Supplier


def setup_admin(app, session):
    if Admin is None or ModelView is None:
        return None

    class DownloadEventAdminView(ModelView):
        can_create = False
        can_edit = False
        can_delete = False
        column_default_sort = ("date_downloaded", True)
        column_list = (
            "date_downloaded",
            "download_type",
            "component_number",
            "component_name",
            "file_name",
            "downloaded_filename",
            "quantity",
            "remote_addr",
        )
        column_searchable_list = (
            "download_type",
            "component_number",
            "component_name",
            "file_name",
            "downloaded_filename",
            "remote_addr",
        )
        column_filters = ("download_type", "date_downloaded", "component_number")

    admin = Admin(app, name="OpenPartsLibrary Admin", template_mode="bootstrap4", url="/admin")
    admin.add_view(ModelView(Component, session, category="Library"))
    admin.add_view(ModelView(File, session, category="Library"))
    admin.add_view(ModelView(Supplier, session, category="Library"))
    admin.add_view(ModelView(Material, session, category="Library"))
    admin.add_view(ModelView(ComponentComponent, session, category="Library"))
    admin.add_view(DownloadEventAdminView(DownloadEvent, session, category="Analytics"))
    return admin

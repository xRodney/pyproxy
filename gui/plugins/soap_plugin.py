from gui.plugins.plugin_registry import GridPlugin


class SoapPlugin(GridPlugin):
    def get_columns(self):
        return (
            ("soap_method", "SOAP method")
        )

    def get_cell_content(self, data, column_id, value):
        if column_id == "soap_method":
            return "Some soap method"

from gui.plugins.plugin_registry import GridPlugin
from utils import soap2python


class SoapPlugin(GridPlugin):
    def get_columns(self):
        return (
            ("soap_method", "SOAP method"),
        )

    def get_cell_content(self, data, column_id, value):
        if column_id == "soap_method":
            if not self.__is_soap(data.request):
                return "--"

            try:
                element = self.__get_element(data.request)
                return element.tag
            except Exception as ex:
                return str(ex)

    def __is_soap(self, request):
        return b"soap" in request.get_content_type() or (
            b"xml" in request.get_content_type() and "schemas.xmlsoap.org" in request.body_as_text())

    def __get_element(self, request):
        element = soap2python.parse_soap_from_string(request.body_as_text())
        return element

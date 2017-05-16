from gui.plugins.plugin_registry import GridPlugin


class CorePlugin(GridPlugin):
    def get_columns(self):
        return (
            ("request", "Request"),
            ("response", "Response")
        )

    def get_cell_content(self, data, column_id, value):
        if column_id == "request":
            msg = data.request
        elif column_id == "response":
            msg = data.response
        else:
            return None

        return msg.first_line().decode().split("\r\n")[0] if msg else "Unmatched"
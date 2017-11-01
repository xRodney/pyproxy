from proxycore.parser.http_parser import HttpResponse, HttpRequest

from proxycore.pipe.recipe.flow import Flow, Transform


class DefaultTransform(Transform):
    def __init__(self):
        pass

    @staticmethod
    def __get_address(address, port=None):
        if port:
            return b"%s:%s" % (str(address).encode(), str(port).encode())
        else:
            return b"%s" % (str(address).encode())

    def local_address_with_port(self, parameters):
        return self.__get_address(parameters.local_address, parameters.local_port)

    def remote_address_with_port(self, parameters):
        return self.__get_address(parameters.remote_address, parameters.remote_port)

    def local_address_without_port(self, parameters):
        return self.__get_address(parameters.local_address)

    def remote_address_without_port(self, parameters):
        return self.__get_address(parameters.remote_address)

    def process_message(self, msg, parameters):
        # self.replace_local_with_remote_in_header(msg, b"Host", parameters)
        # self.replace_local_with_remote_in_header(msg, b"Referer", parameters)
        # self.replace_remote_with_local_in_header(msg, b"Location", parameters)

        if msg.headers.get(b"Transfer-Encoding", "") == b"chunked":
            del msg.headers[b"Transfer-Encoding"]
            msg.headers[b"Content-Length"] = str(len(msg.body)).encode()

        return msg

    def replace_host_in_response_header(self, response, original_host, new_host, header_name):
        header = response.headers.get(header_name)

        if original_host and new_host and header:
            response.headers[header_name] = header.replace(new_host, original_host)

    def transform(self, request: HttpRequest, proxy: Flow, next_in_chain) -> HttpRequest:
        original_host = None
        new_host = None
        if request.headers.get(b"Host") and hasattr(proxy.parameters, "remote_address"):
            if hasattr(proxy.parameters, "remote_port") and proxy.parameters.remote_port == 80:
                new_host = self.remote_address_without_port(proxy.parameters)
            else:
                new_host = self.remote_address_with_port(proxy.parameters)

            original_host = request.headers[b"Host"]
            request.headers[b"Host"] = new_host

        request = self.process_message(request, proxy.parameters)

        response = yield from next_in_chain(request)

        if original_host and new_host:
            self.replace_host_in_response_header(response, original_host, new_host, b"Location")
            self.replace_host_in_response_header(response, original_host, new_host, b"Referer")

        return self.process_message(response, proxy.parameters)


def register_flow(flow: Flow):
    def respond_404(request: HttpRequest):
        response = HttpResponse()
        response.status = b"404"
        response.status_message = b"Nenalezeno bla bla"
        response.body = b"Zkus hledat jinde"
        return response

    # flow.when(lambda request: b"asset" in request.path).then_respond(respond_404)
    flow.transform(DefaultTransform()).call_endpoint("remote")
    return flow

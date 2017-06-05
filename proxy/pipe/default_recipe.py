from proxy.parser.http_parser import HttpResponse, HttpRequest

from proxy.pipe.recipe.transform import Proxy, Transform


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

    def replace_local_with_remote(self, input: bytes, parameters):
        s = input
        s = s.replace(self.local_address_with_port(parameters), self.remote_address_with_port(parameters))
        s = s.replace(self.local_address_without_port(parameters), self.remote_address_without_port(parameters))
        return s

    def replace_remote_with_local(self, input: bytes, parameters):
        s = input
        s = s.replace(self.remote_address_with_port(parameters), self.local_address_with_port(parameters))
        s = s.replace(self.remote_address_without_port(parameters), self.local_address_without_port(parameters))
        return s

    def replace_local_with_remote_in_header(self, msg, header, parameters):
        if msg.headers.get(header):
            msg.headers[header] = self.replace_local_with_remote(msg.headers[header], parameters)

    def replace_remote_with_local_in_header(self, msg, header, parameters):
        if msg.headers.get(header):
            msg.headers[header] = self.replace_remote_with_local(msg.headers[header], parameters)

    def process_message(self, msg, parameters):
        self.replace_local_with_remote_in_header(msg, b"Host", parameters)
        self.replace_local_with_remote_in_header(msg, b"Referer", parameters)
        self.replace_remote_with_local_in_header(msg, b"Location", parameters)

        if msg.headers.get(b"Transfer-Encoding", "") == b"chunked":
            del msg.headers[b"Transfer-Encoding"]
            msg.headers[b"Content-Length"] = str(len(msg.body)).encode()

        return msg

    def transform_response(self, response: HttpResponse, proxy: Proxy) -> HttpResponse:
        return self.process_message(response, proxy.parameters)

    def transform_request(self, request: HttpRequest, proxy: Proxy) -> HttpRequest:
        return self.process_message(request, proxy.parameters)


def recipe(proxy: Proxy):
    proxy.transform(DefaultTransform()).then_pass_through()

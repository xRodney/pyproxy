import collections
import uuid


class RequestResponse:
    def __init__(self, request=None, response=None):
        self.guid = uuid.uuid4()
        self.response = response
        self.request = request

    def __str__(self):
        s = "====================================================\n"
        s += "Communication " + str(self.guid) + "\n"
        s += "REQUEST:\n"
        s += str(self.request) + "\n"
        s += "RESPONSE:\n"
        s += str(self.response) + "\n"
        s += "====================================================\n"
        return s


class Communication:
    def __init__(self, local_address, local_port, remote_address, remote_port, listener=None):
        self.remote_port = remote_port
        self.remote_address = remote_address
        self.local_port = local_port
        self.local_address = local_address

        self.pending_requests = collections.deque()
        self.pending_responses = collections.deque()
        self.listener = listener

    def __get_address(self, address, port):
        if port != 80:
            return b"%s:%s" % (str(address).encode(), str(port).encode())
        else:
            return b"%s" % (str(address).encode())

    def local_address_port(self):
        return self.__get_address(self.local_address, self.local_port)

    def remote_address_port(self):
        return self.__get_address(self.remote_address, self.remote_port)

    def replace_local_with_remote(self, input: bytes):
        return input.replace(self.local_address_port(), self.remote_address_port())

    def replace_remote_with_local(self, input: bytes):
        return input.replace(self.remote_address_port(), self.local_address_port())

    def replace_local_with_remote_in_header(self, msg, header):
        if msg.headers.get(header):
            msg.headers[header] = self.replace_local_with_remote(msg.headers[header])

    def replace_remote_with_local_in_header(self, msg, header):
        if msg.headers.get(header):
            msg.headers[header] = self.replace_remote_with_local(msg.headers[header])

    def process_message(self, msg, tag):
        self.replace_local_with_remote_in_header(msg, b"Host")
        self.replace_local_with_remote_in_header(msg, b"Referer")
        self.replace_remote_with_local_in_header(msg, b"Location")

        if msg.headers.get(b"Transfer-Encoding", "") == b"chunked":
            del msg.headers[b"Transfer-Encoding"]
            msg.headers[b"Content-Length"] = str(len(msg.body)).encode()

        return msg

    def add_message(self, message, tag):
        if tag == "request":
            self.add_request(message)
        elif tag == "response":
            self.add_response(message)
        else:
            raise Exception("Unknown tag " + tag)

    def add_request(self, request):
        if self.pending_responses:
            request_response = self.pending_responses.popleft()
            request_response.request = request
            self.have_request_response(request_response)
        else:
            request_response = RequestResponse(request=request)
            self.pending_requests.append(request_response)
            self.have_request_response(request_response)

    def add_response(self, response):
        if self.pending_requests:
            request_response = self.pending_requests.popleft()
            request_response.response = response
            self.have_request_response(request_response)
        else:
            request_response = RequestResponse(response=response)
            self.pending_responses.append(request_response)
            self.have_request_response(request_response)

    def have_request_response(self, request_response):
        if self.listener:
            self.listener.on_request_response(request_response)


class MessageListener:
    def on_request_response(self, request_response: RequestResponse):
        print(request_response)

    def on_error(self, error):
        print(error)
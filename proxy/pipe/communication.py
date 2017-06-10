import collections
import uuid

from typing import Union

from proxy.parser.http_parser import HttpRequest, HttpResponse, HttpMessage


class RequestResponse:
    def __init__(self, request=None, response=None):
        self.guid = uuid.uuid4()
        self.response = response
        self.request = request
        self.processing = None

    def __str__(self):
        s = "====================================================\n"
        s += "Communication " + str(self.guid) + "\n"
        s += "REQUEST:\n"
        s += str(self.request) + "\n"
        s += "RESPONSE:\n"
        s += str(self.response) + "\n"
        s += "====================================================\n"
        return s

    def set_request_or_response(self, message: HttpMessage):
        if isinstance(message, HttpRequest):
            self.request = message
        elif isinstance(message, HttpResponse):
            self.response = message
        else:
            raise ValueError("Message must be either request or response")


class MessagePairer:
    def __init__(self, listener=None):
        self.pending = collections.deque()
        self.last_class_in_pending = None
        self.listener = listener

    def add_message(self, message: HttpMessage):
        if not isinstance(message, (HttpRequest, HttpResponse)):
            raise Exception("Message must be either request or response")

        if len(self.pending) == 0 or self.last_class_in_pending is message.__class__:
            self.last_class_in_pending = message.__class__
            request_response = RequestResponse()
            self.pending.append(request_response)
        else:
            request_response = self.pending.popleft()

        request_response.set_request_or_response(message)
        self.have_request_response(request_response)

        return request_response

    def add_message_pair(self, request, response):
        request_response = RequestResponse(request, response)
        self.have_request_response(request_response)

    def add_request(self, request: HttpRequest):
        self.add_message(request)

    def add_response(self, response: HttpResponse):
        self.add_message(response)

    def have_request_response(self, request_response):
        if self.listener:
            self.listener.on_request_response(request_response)


class MessageListener:
    def on_request_response(self, request_response: RequestResponse):
        print(request_response)

    def on_error(self, error):
        print(error)


class Endpoint:
    def __init__(self, name: str, writer):
        self.name = name
        self.writer = writer

    async def _write_message(self, message: HttpMessage):
        for data in message.to_bytes():
            self.writer.write(data)
        await self.writer.drain()

    async def on_received(self, message: HttpMessage):
        pass

    async def send(self, message: HttpMessage, processing):
        pass


class InputEndpoint(Endpoint):
    def __init__(self, name: str, writer, processor):
        super().__init__(name, writer)
        self.processor = processor

    async def on_received(self, message: HttpMessage):
        flow = self.processor(message)
        processing = Processing(self.name, flow)
        endpoint_name, message = processing.send_message(None)
        return processing, endpoint_name, message

    async def send(self, message: HttpMessage, processing):
        await self._write_message(message)


class OutputEndpoint(Endpoint):
    def __init__(self, name: str, writer):
        super().__init__(name, writer)
        self.pending_processsings = collections.deque()

    async def send(self, message: HttpMessage, processing):
        self.pending_processsings.append(processing)
        await self._write_message(message)

    async def on_received(self, message: HttpMessage):
        assert len(self.pending_processsings) > 0, "Response without a request"
        processing = self.pending_processsings.popleft()
        endpoint_name, message = processing.send_message(message)
        return processing, endpoint_name, message


class Dispatcher:
    def __init__(self):
        self.endpoints = {}

    def add_endpoint(self, endpoint: Endpoint):
        self.endpoints[endpoint.name] = endpoint

    async def dispatch(self, source_endpoint: Union[str, Endpoint], received_message: HttpMessage):
        if isinstance(source_endpoint, str):
            source_endpoint = self.endpoints[source_endpoint]

        processing, target_endpoint, message_to_send = await source_endpoint.on_received(received_message)

        if isinstance(target_endpoint, str):
            target_endpoint = self.endpoints[target_endpoint]

        await target_endpoint.send(message_to_send, processing)


class Processing:
    def __init__(self, source_endpoint, flow):
        self.source_endpoint = source_endpoint
        self.flow = flow

    def send_message(self, message):
        if self.has_finished():
            raise ValueError("Flow has already finished")

        try:
            return self.flow.send(message)
        except StopIteration as e:
            self.flow = None
            return self.source_endpoint, e.value

    def has_finished(self):
        return self.flow is None

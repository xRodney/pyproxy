import pytest

from proxy.parser.http_parser import HttpRequest, HttpResponse
from proxy.pipe.communication import InputEndpoint, OutputEndpoint, Dispatcher


class TestWriter:
    """
    Dummy for asyncio Writer.
    """

    def __init__(self):
        self.data = b""

    def write(self, data):
        self.data += data

    async def drain(self):
        pass


@pytest.mark.asyncio
async def test_dispatcher():
    def sample_flow(request):
        response1 = yield "first", HttpRequest(b"GET", b"/first" + request.path)
        response2 = yield "second", HttpRequest(b"GET", b"/second" + request.path)

        return HttpResponse(b"200", b"OK", response1.body + response2.body)

    input_endpoint = InputEndpoint("input", TestWriter(), sample_flow)
    first_endpoint = OutputEndpoint("first", TestWriter())
    second_endpoint = OutputEndpoint("second", TestWriter())

    dispatcher = Dispatcher()
    dispatcher.add_endpoint(input_endpoint)
    dispatcher.add_endpoint(first_endpoint)
    dispatcher.add_endpoint(second_endpoint)

    request = HttpRequest(b"GET", b"/sample/path")
    await dispatcher.dispatch("input", request)

    assert b"GET /first/sample/path" in first_endpoint.writer.data

    response1 = HttpResponse(b"200", b"OK", b"first_response\n")
    await dispatcher.dispatch("first", response1)

    assert b"GET /second/sample/path" in second_endpoint.writer.data

    response2 = HttpResponse(b"200", b"OK", b"second_response\n")
    await dispatcher.dispatch("second", response2)

    assert b"200 OK" in input_endpoint.writer.data
    assert b"first_response" in input_endpoint.writer.data
    assert b"second_response" in input_endpoint.writer.data


@pytest.mark.asyncio
async def test_two_flows():
    def sample_flow(request):
        response1 = yield "output", HttpRequest(b"GET", b"/first" + request.path)

        return HttpResponse(b"200", b"OK", response1.body)

    input_endpoint = InputEndpoint("input", TestWriter(), sample_flow)
    output_endpoint = OutputEndpoint("output", TestWriter())

    dispatcher = Dispatcher()
    dispatcher.add_endpoint(input_endpoint)
    dispatcher.add_endpoint(output_endpoint)

    await dispatcher.dispatch("input", HttpRequest(b"GET", b"/sample/path1"))
    await dispatcher.dispatch("input", HttpRequest(b"GET", b"/sample/path2"))

    assert b"GET /first/sample/path1" in output_endpoint.writer.data
    assert b"GET /first/sample/path2" in output_endpoint.writer.data

    await dispatcher.dispatch("output", HttpResponse(b"200", b"OK", b"response1\n"))
    await dispatcher.dispatch("output", HttpResponse(b"200", b"OK", b"response2\n"))

    assert b"200 OK" in input_endpoint.writer.data
    assert b"response1" in input_endpoint.writer.data
    assert b"response2" in input_endpoint.writer.data

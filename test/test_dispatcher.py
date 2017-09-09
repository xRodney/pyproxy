import pytest

from proxycore.parser.http_parser import HttpRequest, HttpResponse
from proxycore.pipe.communication import Dispatcher, FlowDefinition
from proxycore.pipe.endpoint import InputEndpoint, InputEndpointParameters
from test.dummy_io import TestWriter, TestReader, TestOutputEndpoint


@pytest.mark.asyncio
async def test_dispatcher():
    input_endpoint = InputEndpoint("input", InputEndpointParameters("address", 1234, None))
    first_endpoint = TestOutputEndpoint("first", None)
    second_endpoint = TestOutputEndpoint("second", None)

    class SampleDefinition(FlowDefinition):
        def endpoints(self):
            return input_endpoint, first_endpoint, second_endpoint

        def default_flow(self, request):
            response1 = yield "first", HttpRequest(b"GET", b"/first" + request.path)
            response2 = yield "second", HttpRequest(b"GET", b"/second" + request.path)

            return HttpResponse(b"200", b"OK", response1.body + response2.body)

    dispatcher = Dispatcher(SampleDefinition())
    await dispatcher.handle_client("input", None, TestWriter())

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
    input_endpoint = InputEndpoint("input", InputEndpointParameters("address", 1234, None))
    output_endpoint = TestOutputEndpoint("output", None)

    class SampleDefinition(FlowDefinition):
        def endpoints(self):
            return input_endpoint, output_endpoint

        def default_flow(self, request):
            response1 = yield "output", HttpRequest(b"GET", b"/first" + request.path)

            return HttpResponse(b"200", b"OK", response1.body)

    dispatcher = Dispatcher(SampleDefinition())
    await dispatcher.handle_client("input", None, TestWriter())

    await dispatcher.dispatch("input", HttpRequest(b"GET", b"/sample/path1"))
    await dispatcher.dispatch("input", HttpRequest(b"GET", b"/sample/path2"))

    assert b"GET /first/sample/path1" in output_endpoint.writer.data
    assert b"GET /first/sample/path2" in output_endpoint.writer.data

    await dispatcher.dispatch("output", HttpResponse(b"200", b"OK", b"response1\n"))
    await dispatcher.dispatch("output", HttpResponse(b"200", b"OK", b"response2\n"))

    assert b"200 OK" in input_endpoint.writer.data
    assert b"response1" in input_endpoint.writer.data
    assert b"response2" in input_endpoint.writer.data


@pytest.mark.asyncio
async def test_loop():
    request_bytes = b"".join(HttpRequest(b"GET", b"/sample/first", headers={b"X": b"y"}).to_bytes())
    response = HttpResponse(b"200", b"OK", b"This is body")

    input_endpoint = InputEndpoint("input", InputEndpointParameters("address", 1234, None))

    class SampleDefinition(FlowDefinition):
        def endpoints(self):
            return (input_endpoint,)

        def default_flow(self, request):
            yield from []  # needed as we need a generator that never yields
            return response

    dispatcher = Dispatcher(SampleDefinition())
    await dispatcher.handle_client("input", TestReader(request_bytes), TestWriter())

    await dispatcher.loop()

    response_bytes = b"".join(response.to_bytes())
    assert input_endpoint.writer.data == response_bytes

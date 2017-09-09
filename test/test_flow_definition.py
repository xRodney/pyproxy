import asyncio
import sys

import pytest

from proxycore.parser.http_parser import HttpRequest, get_http_request
from proxycore.parser.parser_utils import intialize_parser, parse
from proxycore.pipe.apipe import ProxyParameters, ProxyFlowDefinition
from proxycore.pipe.communication import Server
from proxycore.pipe.reporting import MessageListener
from test.dummy_io import TestReader, TestWriter

__registered_flow = None


def register_flow(flow):
    global __registered_flow
    __registered_flow = flow
    return flow


def test_definition_loading():
    proxy_parameters = ProxyParameters("localhost", 123, "remotehost", 456)
    this_module = sys.modules[__name__]
    definition = ProxyFlowDefinition(proxy_parameters, this_module, MessageListener())
    flow = definition.get_flow("local")

    assert flow
    assert __registered_flow is flow


@pytest.fixture(autouse=True)
def monkeypatch_asyncio():
    async def open_connection(*args, **kwargs):
        return TestReader(b""), TestWriter()

    asyncio.open_connection = open_connection


@pytest.fixture
def server():
    import proxycore.flows
    proxy_parameters = ProxyParameters("localhost", 0, "remotehost", 456)
    definition = ProxyFlowDefinition(proxy_parameters, proxycore.flows, MessageListener())
    server = Server(definition)
    return server


@pytest.mark.asyncio
async def test_duck_service1(server):
    request = HttpRequest(b'POST', b'/DuckService2',
                          headers={
                              b'Accept-Encoding': b'gzip,deflate',
                              b'Content-Type': b'application/soap+xml;charset=UTF-8',
                              b'Content-Length': b'463',
                              b'Host': b'localhost:8889',
                              b'Connection': b'Keep-Alive',
                              b'User-Agent': b'Apache-HttpClient/4.1.1 (java 1.5)',
                          },
                          body=b'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:duck="http://example.com/duck/">\n'
                               b'   <soap:Header/>\n'
                               b'   <soap:Body>\n'
                               b'      <duck:duckAdd>\n'
                               b'         <duck:username>?</duck:username>\n'
                               b'         <duck:password>?</duck:password>\n'
                               b'         <!--1 or more repetitions:-->\n'
                               b'         <duck:settings>\n'
                               b'            <duck:key>?</duck:key>\n'
                               b'            <duck:value>?</duck:value>\n'
                               b'         </duck:settings>\n'
                               b'      </duck:duckAdd>\n'
                               b'   </soap:Body>\n'
                               b'</soap:Envelope>'
                          )

    request_bytes = b"".join(request.to_bytes())
    local_reader = TestReader(request_bytes)
    local_writer = TestWriter()

    await server.handle_client(local_reader, local_writer, "local")

    response_bytes = local_writer.data
    assert response_bytes

    parser = intialize_parser(get_http_request)
    parsed_messages = list(parse(parser, response_bytes))
    response = parsed_messages[0]

    assert response.status == b"200"
    assert b"result>115</" in response.body


@pytest.mark.asyncio
async def test_duck_service2(server):
    request = HttpRequest(b'POST', b'/DuckService2',
                          headers={
                              b'Accept-Encoding': b'gzip,deflate',
                              b'Content-Type': b'application/soap+xml;charset=UTF-8',
                              b'Host': b'localhost:8889',
                              b'Connection': b'Keep-Alive',
                              b'User-Agent': b'Apache-HttpClient/4.1.1 (java 1.5)',
                          },
                          body=b'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:duck="http://example.com/duck/">\n'
                               b'   <soap:Header/>\n'
                               b'   <soap:Body>\n'
                               b'      <duck:duckAdd>\n'
                               b'         <duck:username>test</duck:username>\n'
                               b'         <duck:password>test</duck:password>\n'
                               b'      </duck:duckAdd>\n'
                               b'   </soap:Body>\n'
                               b'</soap:Envelope>'
                          )

    request_bytes = b"".join(request.to_bytes())
    local_reader = TestReader(request_bytes * 2)
    local_writer = TestWriter()

    await server.handle_client(local_reader, local_writer, "local")

    response_bytes = local_writer.data
    assert response_bytes

    parser = intialize_parser(get_http_request)
    parsed_messages = list(parse(parser, response_bytes))
    response1 = parsed_messages[0]
    response2 = parsed_messages[1]

    assert response1.status == b"200"
    assert b"result>42</" in response1.body

    assert response2.status == b"200"
    assert b"result>43</" in response2.body


@pytest.mark.asyncio
async def test_duck_service3(server):
    request = HttpRequest(b'POST', b'/DuckService2',
                          headers={
                              b'Accept-Encoding': b'gzip,deflate',
                              b'Content-Type': b'application/soap+xml;charset=UTF-8',
                              b'Host': b'localhost:8889',
                              b'Connection': b'Keep-Alive',
                              b'User-Agent': b'Apache-HttpClient/4.1.1 (java 1.5)',
                          },
                          body=b'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:duck="http://example.com/duck/">\n'
                               b'   <soap:Header/>\n'
                               b'   <soap:Body>\n'
                               b'      <duck:duckList>\n'
                               b'        <duck:username>?</duck:username>\n'
                               b'      </duck:duckList>\n'
                               b'   </soap:Body>\n'
                               b'</soap:Envelope>'
                          )

    request_bytes = b"".join(request.to_bytes())
    local_reader = TestReader(request_bytes)
    local_writer = TestWriter()

    await server.handle_client(local_reader, local_writer, "local")

    response_bytes = local_writer.data
    assert response_bytes

    parser = intialize_parser(get_http_request)
    parsed_messages = list(parse(parser, response_bytes))
    response = parsed_messages[0]

    assert response.status == b"500"

from proxy.parser import http_parser

import pytest
from proxy.parser.http_parser import HttpResponse
from proxy.parser.parser_utils import intialize_parser, parse
from proxy.pipe.apipe import ProxyParameters
from proxy.pipe.recipe.transform import Proxy, PassThroughMessage, RequestResponseMessage

from proxy.pipe import default_recipe
from proxy.pipe.recipe.matchers import has_method

PARAMETERS = ProxyParameters("localhost", 8888, "remotehost.com", 80)


@pytest.fixture
def simple_get_request():
    msg = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
    parser = intialize_parser(http_parser.get_http_request)
    return list(parse(parser, msg))[0]


@pytest.fixture
def simple_delete_request():
    msg = b"DELETE / HTTP/1.1\r\nHost: localhost\r\n\r\n"
    parser = intialize_parser(http_parser.get_http_request)
    return list(parse(parser, msg))[0]


def responder_200(request):
    response = HttpResponse()
    response.status = b"200"
    response.status_message = b"OK"
    response.body = b"This is body"
    return response


def responder_404(request):
    response = HttpResponse()
    response.status = b"404"
    response.status_message = b"Not found"
    response.body = b"Not found"
    return response

def get_results(processor, request, response):
    processing = processor(request)
    result1 = next(processing)
    try:
        processing.send(response)
    except StopIteration as e:
        return result1, e.value


def test_default_recipe(simple_get_request):
    processor = Proxy(PARAMETERS)
    default_recipe.recipe(processor)

    response = HttpResponse()
    result1, result2 = get_results(processor, simple_get_request, response)

    assert result1 is not None
    assert isinstance(result1, PassThroughMessage)
    assert result1.request.headers[b"Host"] == b"remotehost.com"

    assert result2 is response


def test_pass_through(simple_get_request):
    processor = Proxy(PARAMETERS)
    processor.then_pass_through()

    response = HttpResponse()
    result1, result2 = get_results(processor, simple_get_request, response)

    assert result1 is not None
    assert isinstance(result1, PassThroughMessage)

    assert result2 is response


def test_respond(simple_get_request):
    processor = Proxy(PARAMETERS)
    processor.then_respond(responder_200)

    response = HttpResponse()
    result1, result2 = get_results(processor, simple_get_request, response)
    assert result2 is response

    assert result1 is not None
    assert isinstance(result1, RequestResponseMessage)
    assert result1.request is simple_get_request
    assert result1.response.status == b"200"



def test_has_method(simple_get_request, simple_delete_request):
    processor = Proxy(PARAMETERS)
    processor.when(has_method(b"GET")).then_respond(responder_200)
    processor.when(has_method(b"DELETE")).then_respond(responder_404)

    result1, result2 = get_results(processor, simple_get_request, None)
    assert result1 is not None
    assert isinstance(result1, RequestResponseMessage)
    assert result1.request is simple_get_request
    assert result1.response.status == b"200"

    assert result2 is None

    result1, result2 = get_results(processor, simple_delete_request, None)
    assert result1 is not None
    assert isinstance(result1, RequestResponseMessage)
    assert result1.request is simple_delete_request
    assert result1.response.status == b"404"

    assert result2 is None

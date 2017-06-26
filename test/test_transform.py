import pytest

from proxy.flows import default_recipe
from proxy.parser import http_parser
from proxy.parser.http_parser import HttpResponse, HttpRequest
from proxy.parser.parser_utils import intialize_parser, parse
from proxy.pipe.apipe import ProxyParameters
from proxy.pipe.communication import Processing, ProcessingFinishedError
from proxy.pipe.recipe.matchers import has_method
from proxy.pipe.recipe.transform import Flow

PARAMETERS = ProxyParameters("localhost", 8888, "remotehost.com", 80)


@pytest.fixture
def simple_get_request():
    return HttpRequest(b"GET", b"/", headers={b"Host": b"localhost"})


@pytest.fixture
def response_302():
    return HttpResponse(b"302", b"Found", headers={b"Location": b"http://remotehost.com"})


@pytest.fixture
def simple_delete_request():
    msg = b"DELETE / HTTP/1.1\r\nHost: localhost\r\n\r\n"
    parser = intialize_parser(http_parser.get_http_request)
    return list(parse(parser, msg))[0]


def test_default_recipe(simple_get_request, response_302):
    flow = Flow(PARAMETERS)
    default_recipe.recipe(flow)

    processing = Processing("local", flow(simple_get_request))

    target_endpoint, request = processing.send_message(None)

    assert target_endpoint == "remote"
    assert request is not None
    assert request.headers[b"Host"] == b"remotehost.com"

    target_endpoint, response = processing.send_message(response_302)

    assert target_endpoint == "local"
    assert response is not None
    assert response.headers[b"Location"] == b"http://localhost"

    with pytest.raises(ProcessingFinishedError):
        processing.send_message(HttpResponse())


def test_pass_through(simple_get_request):
    flow = Flow(PARAMETERS)
    flow.then_pass_through()

    processing = Processing("local", flow(simple_get_request))

    target_endpoint, request = processing.send_message(None)

    assert target_endpoint == "remote"
    assert request is simple_get_request

    target_endpoint, response = processing.send_message(response_302)

    assert target_endpoint == "local"
    assert response is response_302

    with pytest.raises(ProcessingFinishedError):
        processing.send_message(HttpResponse())


def test_respond(simple_get_request):
    flow = Flow(PARAMETERS)
    flow.then_respond(lambda request: HttpResponse(b"200", b"OK", b"This is body"))

    processing = Processing("local", flow(simple_get_request))

    target_endpoint, response = processing.send_message(None)

    assert target_endpoint == "local"
    assert response is not None
    assert isinstance(response, HttpResponse)
    assert response.status == b"200"

    with pytest.raises(ProcessingFinishedError):
        processing.send_message(HttpResponse())


def test_has_method(simple_get_request, simple_delete_request):
    flow = Flow(PARAMETERS)
    flow.when(has_method(b"GET")).then_respond(lambda request: HttpResponse(b"200", b"OK", b"This is body"))
    flow.when(has_method(b"DELETE")).then_respond(lambda request: HttpResponse(b"404", b"Not found", b"Not found"))

    processing1 = Processing("local", flow(simple_get_request))
    target_endpoint, response1 = processing1.send_message(None)

    assert target_endpoint == "local"
    assert response1.status == b"200"

    processing2 = Processing("local", flow(simple_delete_request))
    target_endpoint, response2 = processing2.send_message(None)

    assert target_endpoint == "local"
    assert response2.status == b"404"


def test_decorator_syntax(simple_get_request):
    flow = Flow(PARAMETERS)

    @flow.respond_when(has_method(b"GET"))
    def handle(request):
        return HttpResponse(b"200", b"OK", b"This is body")

    processing1 = Processing("local", flow(simple_get_request))
    target_endpoint, response1 = processing1.send_message(None)

    assert target_endpoint == "local"
    assert response1.status == b"200"
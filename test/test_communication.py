from collections import OrderedDict

import pytest

from parser.http_parser import HttpRequest, HttpResponse
from pipe.communication import MessagePairer, MessageListener, RequestResponse


class TestListener(MessageListener):
    def __init__(self):
        self.calls = []
        self.pairs = OrderedDict()

    def on_request_response(self, request_response: RequestResponse):
        self.calls.append(request_response)
        self.pairs[request_response.guid] = request_response

    def assert_calls_and_pairs_number(self, expected_calls, expected_pairs):
        assert len(self.calls) == expected_calls
        assert len(self.pairs) == expected_pairs

    def assert_just_request(self, call_index):
        call = self.calls[call_index]
        assert call.request is not None
        assert call.response is None

    def assert_just_response(self, call_index):
        call = self.calls[call_index]
        assert call.request is None
        assert call.response is not None

    def assert_request_and_response_match(self, call_index):
        call = self.calls[call_index]
        assert call.request is not None
        assert call.response is not None
        assert call.request.body == call.response.body


@pytest.fixture
def pairer():
    return MessagePairer(TestListener())


def request(body):
    req = HttpRequest()
    req.body = body
    return req


def response(body):
    resp = HttpResponse()
    resp.body = body
    return resp


def test_one_request_response(pairer: MessagePairer):
    listener = pairer.listener

    pairer.add_request(request(b"1"))
    listener.assert_calls_and_pairs_number(1, 1)
    listener.assert_just_request(0)

    pairer.add_response(response(b"1"))
    listener.assert_calls_and_pairs_number(2, 1)
    listener.assert_request_and_response_match(1)


def test_one_response_request(pairer: MessagePairer):
    listener = pairer.listener

    pairer.add_response(response(b"1"))
    listener.assert_calls_and_pairs_number(1, 1)
    listener.assert_just_response(0)

    pairer.add_request(request(b"1"))
    listener.assert_calls_and_pairs_number(2, 1)
    listener.assert_request_and_response_match(1)


def test_two_requests_two_responses(pairer: MessagePairer):
    listener = pairer.listener

    pairer.add_request(request(b"1"))
    listener.assert_calls_and_pairs_number(1, 1)
    listener.assert_just_request(0)

    pairer.add_request(request(b"2"))
    listener.assert_calls_and_pairs_number(2, 2)
    listener.assert_just_request(1)

    pairer.add_response(response(b"1"))
    listener.assert_calls_and_pairs_number(3, 2)
    listener.assert_request_and_response_match(2)

    pairer.add_response(response(b"2"))
    listener.assert_calls_and_pairs_number(4, 2)
    listener.assert_request_and_response_match(3)


def test_two_responses_two_requests(pairer: MessagePairer):
    listener = pairer.listener

    pairer.add_response(response(b"1"))
    listener.assert_calls_and_pairs_number(1, 1)
    listener.assert_just_response(0)

    pairer.add_response(response(b"2"))
    listener.assert_calls_and_pairs_number(2, 2)
    listener.assert_just_response(1)

    pairer.add_request(request(b"1"))
    listener.assert_calls_and_pairs_number(3, 2)
    listener.assert_request_and_response_match(2)

    pairer.add_request(request(b"2"))
    listener.assert_calls_and_pairs_number(4, 2)
    listener.assert_request_and_response_match(3)


def test_interleaved(pairer: MessagePairer):
    listener = pairer.listener

    pairer.add_message(response(b"1"))
    listener.assert_calls_and_pairs_number(1, 1)
    listener.assert_just_response(0)

    pairer.add_message(request(b"1"))
    listener.assert_calls_and_pairs_number(2, 1)
    listener.assert_request_and_response_match(1)

    pairer.add_message(request(b"2"))
    listener.assert_calls_and_pairs_number(3, 2)
    listener.assert_just_request(2)

    pairer.add_message(response(b"2"))
    listener.assert_calls_and_pairs_number(4, 2)
    listener.assert_request_and_response_match(3)

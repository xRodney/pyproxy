from io import BufferedIOBase
from uuid import UUID

from parser.http_parser import HttpMessage, get_http_request
from parser.parser_utils import get_word, intialize_parser, parse
from pipe.communication import RequestResponse


def serialize_message(msg: HttpMessage, stream: BufferedIOBase):
    for b in msg.to_bytes():
        stream.write(b)
    stream.write(b"\n")


def serialize_message_pair(rr: RequestResponse, stream: BufferedIOBase):
    stream.write(b"Pair: ")
    stream.write(str(rr.guid.hex).encode())
    stream.write(b"\n")

    if rr.request:
        stream.write(b"Request: ")
        serialize_message(rr.request, stream)
    else:
        stream.write(b"NoRequest\n")

    if rr.response:
        stream.write(b"Response: ")
        serialize_message(rr.response, stream)
    else:
        stream.write(b"NoResponse\n")


def parse_message_pair(data):
    kw, data = yield from get_word(data)
    assert kw == b"Pair:"
    uuid_str, data = yield from get_word(data)
    rr = RequestResponse()
    rr.guid = UUID(hex=uuid_str.decode())

    kw, data = yield from get_word(data)
    if kw == b"Request:":
        rr.request, data = get_http_request(data)

    kw, data = yield from get_word(data)
    if kw == b"Response:":
        rr.response, data = get_http_request(data)

    return rr, data


def parse_message_pairs(stream: BufferedIOBase):
    parser = intialize_parser(parse_message_pair)

    data = stream.read(1024)
    while data:
        for rr in parse(parser, data):
            yield rr
        data = stream.read(1024)

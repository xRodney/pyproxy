from io import BufferedIOBase
from uuid import UUID

from proxycore.parser.http_parser import HttpMessage, get_http_request, get_line
from proxycore.parser.parser_utils import get_word, intialize_parser, parse
from proxycore.pipe.reporting import RequestResponse, LogReport


def serialize_message(msg: HttpMessage, stream: BufferedIOBase):
    for b in msg.to_bytes():
        stream.write(b)
    stream.write(b"\r\n")


def serialize_message_report(report: LogReport, stream: BufferedIOBase):
    stream.write(b"Report: ")
    stream.write(str(report.guid.hex).encode())
    stream.write(b"\r\n")

    for key, pair in report.messages.items():
        stream.write(b"Endpoint " + key.encode() + b"\r\n")

        if report.request:
            stream.write(b"Request: ")
            serialize_message(report.request, stream)
        else:
            stream.write(b"NoRequest\r\n")

        if report.response:
            stream.write(b"Response: ")
            serialize_message(report.response, stream)
        else:
            stream.write(b"NoResponse\r\n")

    stream.write(b"End report\r\n")
    stream.write(b"-------------------------------------------------------------------------------\r\n")


def serialize_message_reports(reports, stream: BufferedIOBase):
    for report in reports:
        serialize_message_report(report, stream)


def parse_message_report(data):
    kw, data = yield from get_word(data)
    assert kw == b"Report:"
    uuid_str, data = yield from get_word(data)
    report = LogReport()
    report.guid = UUID(hex=uuid_str.decode())

    kw, data = yield from get_word(data)
    while kw == b"Endpoint":
        key, data = yield from get_word(data)
        rr = RequestResponse()

        kw, data = yield from get_word(data)
        if kw == b"Request:":
            rr.request, data = yield from get_http_request(data)
            _, data = yield from get_line(data)  # Read the newline

        kw, data = yield from get_word(data)
        if kw == b"Response:":
            rr.response, data = yield from get_http_request(data)
            _, data = yield from get_line(data)  # Read the newline

        report.messages[key.decode()] = rr
        kw, data = yield from get_word(data)

    assert kw == b"End"
    kw, data = yield from get_word(data)
    assert kw == b"report"

    _, data = yield from get_line(data)  # Read the last line with the dashes

    return report, data


def parse_message_reports(stream: BufferedIOBase):
    parser = intialize_parser(parse_message_report)

    data = stream.read(1024)
    while data:
        for rr in parse(parser, data):
            yield rr
        data = stream.read(1024)

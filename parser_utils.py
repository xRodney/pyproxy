SPACES = [ord(x) for x in " \t\r\n"]


def parse(parser, data):
    result = parser.send(data)
    while result is not None:
        yield result
        result = next(parser)


def get_main_loop(parser_func):
    def main_loop():
        data = yield None
        while True:
            result, data = yield from parser_func(data)
            data = yield from get_more(data, result)

    return main_loop


def intialize_parser(parser_func):
    parser = get_main_loop(parser_func)()
    next(parser)
    return parser


def get_word(data: str):
    while not data:
        data = yield from get_more(data)

    lindex = 0
    while data[lindex] not in SPACES:
        lindex += 1
        while len(data) <= lindex:
            data = yield from get_more(data)

    rindex = lindex
    while data[rindex] in SPACES:
        rindex += 1
        while len(data) <= rindex:
            data = yield from get_more(data)

    return data[:lindex], data[rindex:]


def get_until(data, delimiter):
    index = -1
    while index < 0:
        index = data.find(delimiter)
        if index < 0:
            data = yield from get_more(data)

    return data[:index], data[index + len(delimiter):]


def get_bytes(data, count):
    while (len(data) < count):
        data = yield from get_more(data)

    return data[:count], data[count:]


def get_rest(data):
    moredata = yield
    while moredata:
        data += moredata
        moredata = yield

    return data, ""


def get_more(data, result=None):
    moredata = yield result
    if data and moredata:
        return data + moredata
    elif moredata:
        return moredata
    else:
        return data

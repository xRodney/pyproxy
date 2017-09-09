import datetime
import logging
import random
import traceback

from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.matcher import Matcher

import suds.sudsobject
from proxycore.parser.http_parser import HttpResponse
from proxycore.pipe.recipe.flow import Transform, Flow, DoesNotAccept, TransformingFlow
from proxycore.pipe.recipe.matchers import has_path
from suds.bindings.binding import envns
from suds.bindings.document import Document
from suds.sax import Namespace
from suds.sax.element import Element as SaxElement
from suds.xsd.sxbase import XBuiltin
from suds.xsd.sxbasic import Sequence, Complex, Element
from suds.xsd.sxbuiltin import Factory, XInteger, XString, XDateTime, XDate

logger = logging.getLogger(__name__)


class SoapTransform(Transform):
    def __init__(self, client):
        self.client = client
        self.binding = Document(self.client.wsdl)

    def __is_soap(self, request):
        return b"soap" in request.get_content_type() or (
            b"xml" in request.get_content_type() and "Envelope" in request.body_as_text())

    def transform(self, request, proxy: "Flow", next_in_chain):
        if not self.__is_soap(request):
            raise DoesNotAccept()

        text = request.body_as_text()

        messageroot, soapbody = self.binding.read_message(text)

        method_elem = soapbody.children[0]
        selector = getattr(self.client.service, method_elem.name)
        if len(selector.methods) > 1:
            arguments = [child.name for child in method_elem.children]
            selector = selector.accepting_args(*arguments)

        method = selector.method

        soap = self.binding.parse_message(method, messageroot, soapbody, input=True)

        try:
            response = yield from next_in_chain(soap)

            if isinstance(response, HttpResponse):
                return response

            xml = self.binding.write_reply(method, response)

        except Exception as e:
            trace = traceback.format_exception(e.__class__, e, e.__traceback__)
            trace = "".join(trace)
            logger.error(trace)

            xml = SaxElement("Envelope", ns=envns)
            body = SaxElement("Body", ns=envns)
            fault = SaxElement("Fault", ns=envns)
            body.append(fault)
            xml.append(body)

            fault.append(SaxElement("faultcode").setText("Server"))
            fault.append(SaxElement("faultstring").setText(trace))


        http_response = HttpResponse(b"200", b"OK")

        http_response.body = xml.str().encode()

        http_response.headers[b'Content-Type'] = b'text/xml; charset=utf-8'
        http_response.headers[b'Content-Length'] = str((len(http_response.body))).encode()
        return http_response


def soap_transform(client):
    return SoapTransform(client)


class SoapMatches(BaseMatcher):
    def __init__(self, pattern, strict):
        self.pattern = pattern
        self.strict = strict

    def _matches(self, item):
        return SoapMatches.object_matches(self.pattern, item, self.strict)

    @staticmethod
    def object_matches(pattern, item, strict):
        if isinstance(pattern, list):
            return SoapMatches.list_matches(pattern, item, strict)
        elif isinstance(item, list) and not strict:
            return SoapMatches.list_matches((pattern,), item, strict)
        elif isinstance(pattern, dict):
            return SoapMatches.dict_matches(pattern, item, strict)
        elif isinstance(pattern, suds.sudsobject.Object):
            return SoapMatches.suds_object_matches(pattern, item, strict)
        elif isinstance(pattern, Matcher):
            return pattern.matches(item)
        elif callable(pattern):
            return pattern(item)
        else:
            return pattern == item

    @staticmethod
    def list_matches(pattern, item, strict):
        if item is None and not strict:
            item = ()

        if len(pattern) > len(item) or (strict and len(pattern) != len(item)):
            return False

        item_index = 0
        for pattern_index, pattern_value in enumerate(pattern):
            while item_index < len(item):
                item_value = item[item_index]
                if SoapMatches.object_matches(pattern_value, item_value, strict):
                    break
                item_index += 1
            else:  # no break
                return False

        return True

    @staticmethod
    def dict_matches(pattern, item, strict):
        if len(pattern) > len(item) or (strict and len(pattern) != len(item)):
            return False

        for key, value in pattern.items():
            if not SoapMatches.object_matches(value, item[key], strict):
                return False

        return True

    @staticmethod
    def suds_object_matches(pattern, item, strict):
        if isinstance(item, suds.sudsobject.Object):
            if not isinstance(item, pattern.__class__):
                return False

        for key, value in suds.sudsobject.items(pattern):
            if value is None and not strict:
                continue

            try:
                item_value = getattr(item, key, None)
            except AttributeError:
                return False

            if not SoapMatches.object_matches(value, item_value, strict):
                return False

        return True


def soap_matches_loosely(soap_object):
    return SoapMatches(soap_object, strict=False)


def soap_matches_strictly(soap_object):
    return SoapMatches(soap_object, strict=True)


_error_response = HttpResponse(b"500",
                               b"Unmatched request",
                               b"The proxy is unable to mock the request")




class SoapFlow(TransformingFlow):
    ERROR_RESPONSE = object()
    DUMMY_RESPONSE = object()

    def __init__(self, client, path, parameters=None, on_mismatch=None):
        super().__init__(SoapTransform(client), parameters)
        self.client = client
        self.matcher = has_path(path)

        if on_mismatch is SoapFlow.ERROR_RESPONSE:
            self.fallback().respond(_error_response)
        elif on_mismatch is SoapFlow.DUMMY_RESPONSE:
            self.fallback().respond(self.__dummy_response)
        elif on_mismatch is not None:
            raise ValueError("Invalid value of on_mismatch. Can only be None, ERROR_RESPOSE or DUMMY_RESPONSE")

    def __dummy_response(self, service, request=None):
        request = request if request is not None else service
        return default_response(self.client, request)

    def __wrap_call(self, wrapped, default_response):
        def wrapper(request):
            try:
                return wrapped(request)
            except DoesNotAccept:
                yield default_response(request)

        return wrapper

    def __call__(self, request):
        if not self.matcher.matches(request):
            raise DoesNotAccept()
        return super().__call__(request)

    def respond_soap(self, soap_object):
        if isinstance(soap_object, suds.sudsobject.Object):
            obj = soap_object
        elif callable(soap_object) and hasattr(soap_object, "_item"):
            obj = soap_object()
        else:
            name = soap_object.__name__
            if name not in self.factory:
                if name.startswith("handle_"):
                    name = name[7:]
                elif name.startswith("do_"):
                    name = name[3:]

            obj = self.factory[name]()

        matcher = soap_matches_loosely(obj)
        return self.when(matcher).respond

    def respond_soap_strict(self, soap_object):
        matcher = soap_matches_strictly(soap_object)
        return self.when(matcher).respond

    @property
    def factory(self):
        return FactoryWrapper(self.client.factory)


class FactoryWrapper():
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __getattr__(self, item):
        return getattr(self.wrapped, item)

    def __getitem__(self, item):
        return self.wrapped[item]

    def __call__(self, *args, **kwargs):
        return dict(**kwargs)


def default_response(client, request):
    selector = getattr(client.service, request.__class__.__name__)

    # TODO: This is alrady done in soap_transform, maybe we could somehow pass the result along the chain?
    if selector.method is not None:  # Method is not overloaded
        method = selector.method
    else:
        method = selector.get_method(**suds.asdict(request))

    output = method.soap.output
    element = client.wsdl.schema.elements[output.body.parts[0].element]

    return __get_default_element(client, element)


def __get_default_element(client, element):
    if element.rawchildren:
        rawchildren = element.rawchildren
    else:
        type = element.cache['resolved:nb=False']  # TODO: What is this?
        rawchildren = type.rawchildren

    if not rawchildren:
        return __get_default_basic_item(client, type)

    response_type = rawchildren[0]

    type_name = element.type[0] if element.type else element.name
    response = __get_default_item(client, response_type, type_name)

    return response


def __get_default_item(client, type, name):
    if isinstance(type, Complex):
        return __get_default_complex_item(client, type, name)
    elif isinstance(type, Sequence):
        obj = getattr(client.factory, name)()
        __fill_default_sequence(client, type, obj)
        return obj
    elif isinstance(type, Element):
        return __get_default_element(client, type)
    else:
        return __get_default_basic_item(client, type)


def __get_default_complex_item(client, type, name):
    obj = getattr(client.factory, name)()
    if len(type.rawchildren) == 1 and isinstance(type.rawchildren[0], Sequence):
        __fill_default_sequence(client, type.rawchildren[0], obj)
    return obj


def __fill_default_sequence(client, sequence, target):
    for el in sequence.rawchildren:
        obj = __get_default_item(client, el, el.name)
        setattr(target, el.name, obj)


def __get_default_basic_item(client, type):
    if type.default:
        return type.default

    if Namespace.xsd(type.type) or Namespace.xsd(type):
        clazz = Factory.tags.get(type.type[0])
    elif isinstance(type, XBuiltin):
        clazz = type.__class__
    else:
        clazz = None

    if clazz == XInteger:
        return __get_next()
    elif clazz == XString:
        return "??? {} ???".format(__get_next())
    elif clazz == XDateTime:
        return datetime.datetime.utcfromtimestamp(__get_next())
    elif clazz == XDate:
        return datetime.datetime.utcfromtimestamp(__get_next())
    else:
        # TODO: More to come
        return __get_next()


__counter = random.randrange(100000)


def __get_next():
    global __counter
    __counter += 1
    return __counter

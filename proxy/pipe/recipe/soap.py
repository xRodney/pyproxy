from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.matcher import Matcher

import suds.sudsobject
from proxy.parser.http_parser import HttpResponse
from proxy.pipe.recipe.flow import Transform, Flow, DoesNotAccept, TransformingFlow
from proxy.pipe.recipe.matchers import has_path
from proxy.pipe.recipe.suds_binding import ServerDocumentBinding


class SoapTransform(Transform):
    def __init__(self, client):
        self.client = client
        self.binding = ServerDocumentBinding(self.client.wsdl)

    def __is_soap(self, request):
        return b"soap" in request.get_content_type() or (
            b"xml" in request.get_content_type() and "schemas.xmlsoap.org" in request.body_as_text())

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

        xml, soap = self.binding.parse_message(method, messageroot, soapbody, input=True)

        response = yield from next_in_chain(soap)

        if isinstance(response, HttpResponse):
            return response

        http_response = HttpResponse(b"200", b"OK")

        xml = self.binding.write_reply(method, response)
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
                item_value = getattr(item, key)
            except AttributeError:
                return False

            if not SoapMatches.object_matches(value, item_value, strict):
                return False

        return True


def soap_matches_loosely(soap_object):
    return SoapMatches(soap_object, strict=False)


def soap_matches_strictly(soap_object):
    return SoapMatches(soap_object, strict=True)


class SoapFlow(TransformingFlow):
    def __init__(self, client, path, parameters=None):
        super().__init__(SoapTransform(client), parameters)
        self.client = client
        self.matcher = has_path(path)

    def __call__(self, request):
        if not self.matcher.matches(request):
            raise DoesNotAccept()
        return super().__call__(request)

    def respond_soap(self, soap_object):
        matcher = soap_matches_loosely(soap_object)
        return self.when(matcher).then_respond

    def respond_soap_strict(self, soap_object):
        matcher = soap_matches_strictly(soap_object)
        return self.when(matcher).then_respond

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

from hamcrest.core.base_matcher import BaseMatcher

from proxy.pipe.recipe import Transform


class SoapTransform(Transform):
    def __init__(self, client):
        self.client = client


def soap_transform(client):
    return SoapTransform(client)


class SoapMatches(BaseMatcher):
    def __init__(self, soap_object, strict):
        self.soap_object = soap_object
        self.strict = strict


def soap_matches_loosely(soap_object):
    return SoapMatches(soap_object, strict=False)


def soap_matches_strictly(soap_object):
    return SoapMatches(soap_object, strict=True)
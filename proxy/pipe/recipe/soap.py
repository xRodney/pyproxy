from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.matcher import Matcher

from proxy.pipe.recipe.transform import Transform


class SoapTransform(Transform):
    def __init__(self, client):
        self.client = client


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
        elif isinstance(pattern, dict):
            return SoapMatches.dict_matches(pattern, item, strict)
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


def soap_matches_loosely(soap_object):
    return SoapMatches(soap_object, strict=False)


def soap_matches_strictly(soap_object):
    return SoapMatches(soap_object, strict=True)
from hamcrest import greater_than

import suds
from proxycore.pipe.recipe.soap import SoapMatches


def test_list_matcher():
    assert SoapMatches.list_matches([], [], strict=True)
    assert SoapMatches.list_matches([], [], strict=False)
    assert not SoapMatches.list_matches([], [1], strict=True)
    assert SoapMatches.list_matches([], [1], strict=False)

    assert SoapMatches.list_matches([1, 2], [1, 2], strict=True)
    assert SoapMatches.list_matches([1, 2], [1, 2], strict=False)

    assert not SoapMatches.list_matches([1, 2], [1, 2, 3], strict=True)
    assert SoapMatches.list_matches([1, 2], [1, 2, 3], strict=False)

    assert not SoapMatches.list_matches([1, 3], [1, 2, 3], strict=True)
    assert SoapMatches.list_matches([1, 3], [1, 2, 3], strict=False)

    assert not SoapMatches.list_matches([2, 3], [1, 2, 3], strict=True)
    assert SoapMatches.list_matches([2, 3], [1, 2, 3], strict=False)

    assert not SoapMatches.list_matches([1, 4], [1, 2, 3], strict=True)
    assert not SoapMatches.list_matches([1, 4], [1, 2, 3], strict=False)

    assert not SoapMatches.list_matches([1, 2, 3, 4], [1, 2, 3], strict=True)
    assert not SoapMatches.list_matches([1, 2, 3, 4], [1, 2, 3], strict=False)

    assert not SoapMatches.list_matches([1, 1, 1], [1, 1, 1, 1], strict=True)
    assert SoapMatches.list_matches([1, 1, 1], [1, 1, 1, 1], strict=False)
    assert SoapMatches.list_matches([1, 1, 1, 2], [1, 1, 1, 1, 2], strict=False)


def test_dict_matcher():
    assert SoapMatches.dict_matches({}, {}, strict=True)
    assert SoapMatches.dict_matches({}, {}, strict=False)
    assert not SoapMatches.dict_matches({}, {"first": 1}, strict=True)
    assert SoapMatches.dict_matches({}, {"first": 1}, strict=False)

    assert SoapMatches.dict_matches({"first": 1, "second": 2}, {"first": 1, "second": 2}, strict=True)
    assert SoapMatches.dict_matches({"first": 1, "second": 2}, {"first": 1, "second": 2}, strict=False)
    assert SoapMatches.dict_matches({"second": 2, "first": 1}, {"first": 1, "second": 2}, strict=True)
    assert not SoapMatches.dict_matches({"second": 22, "first": 1}, {"first": 1, "second": 2}, strict=False)

    assert not SoapMatches.dict_matches({"first": 1, "second": 2}, {"first": 1, "second": 2, "third": 3}, strict=True)
    assert SoapMatches.dict_matches({"first": 1, "second": 2}, {"first": 1, "second": 2, "third": 3}, strict=False)

    assert not SoapMatches.dict_matches({"first": 1, "second": 2}, {"first": 1}, strict=True)
    assert not SoapMatches.dict_matches({"first": 1, "second": 2}, {"first": 1}, strict=False)


def test_combined_matchers():
    assert SoapMatches.object_matches({"first": 1, "list": ['a', 'b']},
                                      {"first": 1, "second": 2, 'list': ['a', 'b', 'c']}, strict=False)

    assert SoapMatches.object_matches(lambda obj: len(obj) == 2,
                                      {"first": 1, "list": ['a', 'b']},
                                      strict=True)

    assert not SoapMatches.object_matches({"first": 1, "list": lambda obj: len(obj) != 2},
                                          {"first": 1, "list": ['a', 'b']},
                                          strict=True)

    assert not SoapMatches.object_matches({"first": greater_than(2)},
                                          {"first": 1, "list": ['a', 'b']},
                                          strict=False)

    assert SoapMatches.object_matches({"first": greater_than(0)},
                                      {"first": 1, "list": ['a', 'b']},
                                      strict=False)


def test_soap():
    client = suds.client.Client("http://www.webservicex.net/CurrencyConvertor.asmx?WSDL")
    factory = client.factory

    pattern = factory.ConversionRate(FromCurrency="USD")
    request = factory.ConversionRate(FromCurrency="USD", ToCurrency = "GBP")

    assert SoapMatches.object_matches(pattern, request, strict=False)
    assert not SoapMatches.object_matches(pattern, request, strict=True)

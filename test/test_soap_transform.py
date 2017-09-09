import os

import suds
import suds.sudsobject
from proxycore.parser.http_parser import HttpRequest
from proxycore.pipe.apipe import ProxyParameters
from proxycore.pipe.endpoint import Processing
from proxycore.pipe.recipe.flow import Flow
from proxycore.pipe.recipe.soap import soap_transform, default_response, SoapFlow
from suds.bindings.document import Document

PARAMETERS = ProxyParameters("localhost", 8888, "remotehost.com", 80)

request = HttpRequest(b'POST', b'/DuckService2',
                      headers={
                          b'Accept-Encoding': b'gzip,deflate',
                          b'Content-Type': b'application/soap+xml;charset=UTF-8',
                          b'Content-Length': b'475',
                          b'Host': b'www.webservicex.net',
                          b'Connection': b'Keep-Alive',
                          b'User-Agent': b'Apache-HttpClient/4.1.1 (java 1.5)',
                          b'X-Original-Host': b'localhost:8888',
                      },
                      body=b'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" '
                           b' xmlns:duck="http://example.com/duck/">\n'
                           b'   <soap:Header/>\n'
                           b'   <soap:Body>\n'
                           b'      <duck:duckAdd>\n'
                           b'         <duck:username>user</duck:username>\n'
                           b'         <duck:password>pass</duck:password>\n'
                           b'         <!--1 or more repetitions:-->\n'
                           b'         <duck:settings>\n'
                           b'            <duck:key>key</duck:key>\n'
                           b'            <duck:value>value</duck:value>\n'
                           b'         </duck:settings>\n'
                           b'      </duck:duckAdd>\n'
                           b'   </soap:Body>\n'
                           b'</soap:Envelope>'
                      )

narwhals_request = HttpRequest(b'POST', b'/narwhals/WebService.asmx',
                               headers={
                                   b'Accept-Encoding': b'gzip,deflate',
                                   b'Content-Type': b'text/xml;charset=UTF-8',
                                   b'SOAPAction': b'"http://narwhals.example.com/Login"',
                                   b'Content-Length': b'465',
                                   b'Host': b'www.httpwatch.com',
                                   b'Connection': b'Keep-Alive',
                                   b'User-Agent': b'Apache-HttpClient/4.1.1 (java 1.5)',
                               },
                               body=b'<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:nar="http://narwhals.example.com">\n'
                                    b'   <soapenv:Header/>\n'
                                    b'   <soapenv:Body>\n'
                                    b'      <nar:Login>\n'
                                    b'         <!--Optional:-->\n'
                                    b'         <nar:username>username</nar:username>\n'
                                    b'         <!--Optional:-->\n'
                                    b'         <nar:password>password</nar:password>\n'
                                    b'         <!--Optional:-->\n'
                                    b'         <nar:remoteAddress>remoteaddress</nar:remoteAddress>\n'
                                    b'      </nar:Login>\n'
                                    b'   </soapenv:Body>\n'
                                    b'</soapenv:Envelope>'
                               )


def test_soap_transform_request():
    flow = Flow(PARAMETERS)

    realpath = os.path.realpath(__file__)
    dir = os.path.dirname(realpath)
    url = 'file://' + dir + "/DuckService2.wsdl"
    client = suds.client.Client(url)

    soap_flow = flow.transform(soap_transform(client))

    @soap_flow.respond
    def handle(request):
        assert isinstance(request, suds.sudsobject.Object)
        response = client.factory.duckAddResponse(result=42)
        return response

    processing1 = Processing("local", flow(request))
    target_endpoint, response1 = processing1.send_message(None)

    assert target_endpoint == "local"
    assert response1.status == b"200"
    assert "result>42</" in response1.body_as_text()


def test_default_response1():
    flow = Flow(PARAMETERS)

    realpath = os.path.realpath(__file__)
    dir = os.path.dirname(realpath)
    url = 'file://' + dir + "/DuckService2.wsdl"
    client = suds.client.Client(url)

    soap_flow = flow.transform(soap_transform(client))

    @soap_flow.respond
    def handle(request):
        assert isinstance(request, suds.sudsobject.Object)
        response = default_response(client, request)
        return response

    processing1 = Processing("local", flow(request))
    target_endpoint, response1 = processing1.send_message(None)

    assert target_endpoint == "local"
    assert response1.status == b"200"
    text = response1.body_as_text()

    binding = Document(client.wsdl)
    method = client.service.duckAdd.method
    parsed = binding.get_reply(method, text)
    assert isinstance(parsed[1], int)


def test_default_response2():
    flow = Flow(PARAMETERS)

    realpath = os.path.realpath(__file__)
    dir = os.path.dirname(realpath)
    url = 'file://' + dir + "/Narwhals.wsdl"
    client = suds.client.Client(url)

    class Service:
        flow = SoapFlow(client, b'/narwhals/WebService.asmx', on_mismatch=SoapFlow.DUMMY_RESPONSE)

    flow.delegate(Service().flow)

    processing1 = Processing("local", flow(narwhals_request))
    target_endpoint, response1 = processing1.send_message(None)

    assert target_endpoint == "local"
    assert response1.status == b"200"
    text = response1.body_as_text()

    binding = Document(client.wsdl)
    method = client.service.Login.method
    parsed = binding.get_reply(method, text)
    assert "???" in parsed[1]


def test_default_response3():
    flow = Flow(PARAMETERS)

    realpath = os.path.realpath(__file__)
    dir = os.path.dirname(realpath)
    url = 'file://' + dir + "/Narwhals.wsdl"
    client = suds.client.Client(url)

    flow.delegate(SoapFlow(client, b"/narwhals/WebService.asmx", on_mismatch=SoapFlow.DUMMY_RESPONSE))

    request = HttpRequest(b'POST', b'/narwhals/WebService.asmx',
                          headers={
                              b'Accept-Encoding': b'gzip,deflate',
                              b'Content-Type': b'text/xml;charset=UTF-8',
                              b'SOAPAction': b'"http://narwhals.example.com/ViewRequest"',
                              b'Content-Length': b'357',
                              b'Host': b'localhost:8889',
                              b'Connection': b'Keep-Alive',
                              b'User-Agent': b'Apache-HttpClient/4.1.1 (java 1.5)',
                          },
                          body=b'<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:nar="http://narwhals.example.com">\n'
                               b'   <soapenv:Header/>\n'
                               b'   <soapenv:Body>\n'
                               b'      <nar:ViewRequest>\n'
                               b'         <!--Optional:-->\n'
                               b'         <nar:sessionKey>?</nar:sessionKey>\n'
                               b'         <nar:requestId>123</nar:requestId>\n'
                               b'      </nar:ViewRequest>\n'
                               b'   </soapenv:Body>\n'
                               b'</soapenv:Envelope>'
                          )

    processing1 = Processing("local", flow(request))
    target_endpoint, response1 = processing1.send_message(None)

    assert target_endpoint == "local"
    assert response1.status == b"200"
    text = response1.body_as_text()

    binding = Document(client.wsdl)
    method = client.service.ViewRequest.method
    parsed = binding.get_reply(method, text)
    assert parsed[1].Notes.NoteInfo[0].Created


def test_soap_matches_instance():
    flow = Flow(PARAMETERS)

    realpath = os.path.realpath(__file__)
    dir = os.path.dirname(realpath)
    url = 'file://' + dir + "/DuckService2.wsdl"
    client = suds.client.Client(url)

    class Service:
        flow = SoapFlow(client, b'/DuckService2')

        @flow.respond_soap(flow.factory.duckAdd())
        def name_does_not_matter(self, request):
            return self.flow.factory.duckAddResponse(
                result=115
            )

    flow.delegate(Service().flow)

    processing1 = Processing("local", flow(request))
    target_endpoint, response1 = processing1.send_message(None)

    assert target_endpoint == "local"
    assert response1.status == b"200"
    text = response1.body_as_text()

    binding = Document(client.wsdl)
    method = client.service.duckAdd.method
    _, parsed = binding.get_reply(method, text)
    assert parsed == 115


def test_soap_matches_method():
    flow = Flow(PARAMETERS)

    realpath = os.path.realpath(__file__)
    dir = os.path.dirname(realpath)
    url = 'file://' + dir + "/DuckService2.wsdl"
    client = suds.client.Client(url)

    class Service:
        flow = SoapFlow(client, b'/DuckService2')
        xx = flow.factory.duckAdd

        @flow.respond_soap(flow.factory.duckAdd)
        def name_does_not_matter(self, request):
            return self.flow.factory.duckAddResponse(
                result=115
            )

    flow.delegate(Service().flow)

    processing1 = Processing("local", flow(request))
    target_endpoint, response1 = processing1.send_message(None)

    assert target_endpoint == "local"
    assert response1.status == b"200"
    text = response1.body_as_text()

    binding = Document(client.wsdl)
    method = client.service.duckAdd.method
    _, parsed = binding.get_reply(method, text)
    assert parsed == 115

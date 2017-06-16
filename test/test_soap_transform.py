import os

import suds
import suds.sudsobject
from proxy.parser.http_parser import HttpRequest
from proxy.pipe.apipe import ProxyParameters
from proxy.pipe.communication import Processing
from proxy.pipe.recipe.soap import soap_transform
from proxy.pipe.recipe.transform import Proxy

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


def test_soap_transform_request():
    flow = Proxy(PARAMETERS)

    realpath = os.path.realpath(__file__)
    dir = os.path.dirname(realpath)
    url = 'file://' + dir + "/DuckService2.wsdl"
    client = suds.client.Client(url)

    soap_flow = flow.transform(soap_transform(client))

    @soap_flow.then_respond
    def handle(request):
        assert isinstance(request, suds.sudsobject.Object)
        response = client.factory.duckAddResponse()
        setattr(response, "return", 42)
        return response

    processing1 = Processing("local", flow(request))
    target_endpoint, response1 = processing1.send_message(None)

    assert target_endpoint == "local"
    assert response1.status == b"200"
    assert "return>42</" in response1.body_as_text()

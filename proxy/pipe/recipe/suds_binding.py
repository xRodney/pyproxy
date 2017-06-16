import suds.bindings.document
from suds.sax.document import Document
from suds.sax.parser import Parser


class ServerDocumentBinding(suds.bindings.document.Document):
    """
    The soap binding class used to process outgoing and imcoming
    soap messages per the WSDL port binding.
    @cvar replyfilter: The reply filter function.
    @type replyfilter: (lambda s,r: r)
    @ivar wsdl: The wsdl.
    @type wsdl: L{suds.wsdl.Definitions}
    @ivar schema: The collective schema contained within the wsdl.
    @type schema: L{xsd.schema.Schema}
    @ivar options: A dictionary options.
    @type options: L{Options}
    """

    def __init__(self, wsdl):
        super().__init__(wsdl)

    def read_message(self, message):
        sax = Parser()
        messageroot = sax.parse(string=message)
        soapenv = messageroot.getChild('Envelope')
        soapenv.promotePrefixes()
        soapbody = soapenv.getChild('Body')
        self.detect_fault(soapbody)
        self.multiref.process(soapbody)
        return messageroot, soapbody

    def parse_message(self, method, messageroot, soapbody=None, input=False):
        if not soapbody:
            soapenv = messageroot.getChild('Envelope')
            soapenv.promotePrefixes()
            soapbody = soapenv.getChild('Body')

        nodes = soapbody.children
        rtypes = self.bodypart_types(method, input=input)
        rtypes = [rt[1] if isinstance(rt, tuple) else rt for rt in rtypes]
        if len(rtypes) > 1:
            result = self.replycomposite(rtypes, nodes)
            return (messageroot, result)
        if len(rtypes) == 1:
            if rtypes[0].unbounded():
                result = self.replylist(rtypes[0], nodes)
                return (messageroot, result)
            if len(nodes):
                unmarshaller = self.unmarshaller()
                resolved = rtypes[0].resolve(nobuiltin=True)
                result = unmarshaller.process(nodes[0], resolved)
                return (messageroot, result)
        return (messageroot, None)

    def write_reply(self, method, obj):
        """
        Get the soap message for the specified method, args and soapheaders.
        This is the entry point for creating the outbound soap message.
        @param method: The method being invoked.
        @type method: I{service.Method}
        @param args: A list of args for the method invoked.
        @type args: list
        @param kwargs: Named (keyword) args for the method invoked.
        @type kwargs: dict
        @return: The soap envelope.
        @rtype: L{Document}
        """

        content = self.headercontent(method)
        header = self.header(content)

        element = method.soap.output.body.parts[0].element
        pd = self.wsdl.schema.elements[element]

        content = self.mkparam(method, (element[0], pd), obj)
        body = self.body(content)
        env = self.envelope(header, body)
        if self.options().prefixes:
            body.normalizePrefixes()
            env.promotePrefixes()
        else:
            env.refitPrefixes()
        return Document(env)

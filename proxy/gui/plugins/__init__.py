from proxy.gui.plugins.cmd_plugin import CmdPlugin
from proxy.gui.plugins.core_plugin import CorePlugin
from proxy.gui.plugins.request_plugin import RequestPlugin

from proxy.gui.plugins.soap_plugin import SoapPlugin

PLUGINS = [CorePlugin(), SoapPlugin(), RequestPlugin(), CmdPlugin()]

from proxygui.plugins.code_gen_plugin import CodeGenPlugin
from .cmd_plugin import CmdPlugin
from .core_plugin import CorePlugin
from .request_plugin import RequestPlugin

from .soap_plugin import SoapPlugin

PLUGINS = [CorePlugin(), SoapPlugin(), RequestPlugin(), CmdPlugin(), CodeGenPlugin()]

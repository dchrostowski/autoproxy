from py_mini_racer import py_mini_racer
from IPython import embed
import base64
ctx = py_mini_racer.MiniRacer()

js_code = """
var a = '.581.86'.split('').reverse().join('')
var yxy = '\x4e\x54\x63\x75\x4e\x6a\x59\x3d'.replace(/\\x([0-9A-Fa-f]{2})/g, function () { return String.fromCharCode(parseInt(arguments[1], 16)) })
var pp = (65 - ([] + []))/**//**//**/ +  15 - [] + []
"""
ctx.eval(js_code)
addr1 = ctx.eval("a")
port = ctx.eval("pp")
addr2 = base64.b64decode(ctx.eval("yxy"))

embed()
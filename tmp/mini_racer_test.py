from py_mini_racer import py_mini_racer
from IPython import embed
import base64
ctx = py_mini_racer.MiniRacer()
embed()

ctx.eval("""
document.open()
document.write('<html><body><div id="possum">he scream at own ass</div></body></html>')
document.close()
""")

embed()
js_code = """
var a = '.581.86'.split('').reverse().join('')
var yxy = '\x4e\x54\x63\x75\x4e\x6a\x59\x3d'.replace(/\\x([0-9A-Fa-f]{2})/g, function () { return String.fromCharCode(parseInt(arguments[1], 16)) })
var pp = (65 - ([] + []))/**//**//**/ +  15 - [] + []
"""

def_atob = "var atob = function(arg) { return arg };"
ratob = "var yxy = /* *//* *//* *//* */ atob('\x4d\x7a\x6b\x75\x4d\x54\x67\x3d'.replace(/\\x([0-9A-Fa-f]{2})/g,function(){return String.fromCharCode(parseInt(arguments[1], 16))}));"

ctx.eval(js_code)
addr1 = ctx.eval("a")
port = int(ctx.eval("pp"))
addr2 = base64.b64decode(ctx.eval("yxy")).decode('utf-8')
address = "%s%s" % (addr1,addr2)

embed()
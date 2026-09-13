"""Run the binding probe under the game's actual Mono, without opening Unity."""
import os
import ctypes as c
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[4]
g=root.parent.parent/'GmodeArchivesPlus_kibu8'
out=root/'games/08-kibu8/reports'
sdk=subprocess.check_output(['dotnet','--list-sdks'],text=True).strip().splitlines()[-1]
compiler=Path(sdk[sdk.index('[')+1:-1])/sdk.split()[0]/'Roslyn/bincore/csc.dll'
files=[Path(__file__).with_name('MonoBindingProbe.cs'),root/'engine/adapters/gmode-20050817/RuntimePack.cs',root/'engine/core/TranslationPackReader.cs',root/'engine/core/TranslationCatalog.cs',root/'games/08-kibu8/bepinex/src/ScriptIdentityData.cs']
subprocess.run(['dotnet',str(compiler),'-nologo','-nostdlib+','-target:library','-out:'+str(out/'MonoBindingProbe.dll')]+['-r:'+str(g/'kibu8_Data/Managed'/n) for n in ['mscorlib.dll','System.dll','System.Core.dll']]+list(map(str,files)),check=True)
os.environ['KIBU8_PROBE_WORK']=str(root/'games/08-kibu8')
os.environ['KIBU8_PROBE_ASSEMBLY']=str(g/'kibu8_Data/Managed/Assembly-CSharp.dll')
m=c.CDLL(str(g/'MonoBleedingEdge/EmbedRuntime/mono-2.0-bdwgc.dll'))
def fn(n,r,*a):
 f=getattr(m,n);f.restype=r;f.argtypes=list(a);return f
ptr=c.c_void_p;s=c.c_char_p
fn('mono_set_assemblies_path',None,s)(str(g/'kibu8_Data/Managed').encode())
d=fn('mono_jit_init_version',ptr,s,s)(b'probe',b'v4.0.30319')
a=fn('mono_domain_assembly_open',ptr,ptr,s)(d,str(out/'MonoBindingProbe.dll').encode())
im=fn('mono_assembly_get_image',ptr,ptr)(a)
cl=fn('mono_class_from_name',ptr,ptr,s,s)(im,b'',b'MonoBindingProbe')
method=fn('mono_class_get_method_from_name',ptr,ptr,s,c.c_int)(cl,b'Run',0)
e=ptr();result=fn('mono_runtime_invoke',ptr,ptr,ptr,ptr,c.POINTER(ptr))(method,None,None,c.byref(e))
assert not e.value,'Unhandled managed exception'
text=fn('mono_string_to_utf8',s,ptr)(result).decode();print(text)
raise SystemExit(0 if text.startswith('PASS') else 1)

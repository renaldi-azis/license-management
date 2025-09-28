import HttpAntiDebug as hd
from HttpAntiDebug import SessionServer as SV

sess = SV('https://ricthoolsquantri.online')

rs = hd.get('https://richtoolsquantri.online')
if rs.status_code == 200:
    print(rs.text)
print(rs.status_code)
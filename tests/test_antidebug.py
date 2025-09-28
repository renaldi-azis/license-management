import HttpAntiDebug
from HttpAntiDebug import SessionServer as SV

sess = SV('https://jsonip.com')

print(sess.get('/').text)
sess.get('https://jsonip.com',)

# req = HttpAntiDebug.get("https://richtoolsmmo.com")
# print(req.status_code)
# print(req.text)
# print(req.headers)

import requests
response = requests.get("https://103.152.165.248", verify=False)
print(response.status_code)

# import socket
# try:
#     domain = socket.gethostbyaddr("103.152.165.248")
#     print(f"IP resolves to: {domain}")
# except:
#     print("Reverse DNS lookup failed")

req = HttpAntiDebug.get("https://103.152.165.248")
print(req.status_code)
print(req.text)
print(req.headers)
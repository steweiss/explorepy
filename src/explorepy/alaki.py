import numpy as np
#bin_data=b'\xff\xbe\xaf\x7e\xad\xde'
#dec_data=np.asarray([int.from_bytes(bin_data[x:x + 3],
 #                                         byteorder='little',
  #                                        signed=True) for x in range(0, len(bin_data), 3)])
#print(dec_data)

from bluetooth import *
from pprint import pprint
devices = discover_devices()
services = find_service()
print(devices)
service = find_service(address='00:13:43:69:83:4F')
pprint(service)
print(services)

'''
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print(s)
server = 'pythonprogramming.net'
port = 80
server_ip = socket.gethostbyname(server)
print(server_ip)
request = "GET /HTTP/1.1\nHOST: "+server+"\n\n"
s.connect((server, port))
s.send(request.encode())
result = s.recv(4096)
while (len(result)>0):
    print(result)
    result = s.recv(4096)
'''

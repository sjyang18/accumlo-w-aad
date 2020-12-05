#!/usr/bin/python3

import base64
import getpass

passwd = getpass.getpass(prompt="password :")

ad_formatted_pwd = '"{}"'.format(passwd)
message_byptes = ad_formatted_pwd.encode('utf-16-le')
base64_bytes = base64.b64encode(message_byptes)
output = ":{}".format(base64_bytes.decode('utf-8'))
print(output)
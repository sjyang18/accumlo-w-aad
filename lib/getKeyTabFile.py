import os
import getpass
from subprocess import run, PIPE

def getKeyTabFile():
    domainuser = input("domain user name (i.e. user@DOMAIN.COM): ")
    passwd = getpass.getpass(prompt="password: ")

    input_load = f"""add_entry -password -p {domainuser} -k 1 -e RC4-HMAC
    {passwd}
    wkt user.keytab
    q
"""
    p = run(['ktutil'], stdout=PIPE, input=input_load, encoding='ascii', shell=True)


if __name__ == "__main__":
    getKeyTabFile()

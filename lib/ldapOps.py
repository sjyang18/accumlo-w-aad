import os
import getpass
from subprocess import run, PIPE


passwd = getpass.getpass(prompt="password :")


def test_ldapsearch(passwd):
    cmd = ['ldapsearch', '-x', '-w', passwd]
    p = run(cmd, encoding='ascii')
    if p.returncode != 0:
        print("Error in ldapsearch")
    else:
        print("Success")

def create_custom_ou(ouname):
    pass

if __name__ == "__main__":
    passwd =  getpass.getpass(prompt="password :")
    #test_ldapsearch(passwd)

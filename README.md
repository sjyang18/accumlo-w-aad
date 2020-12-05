# Accumulo with AAD Integration Tooling

## Join Azure VMSS (with Centos OS) to Azure Active Directory (AAD) Domain Services & Setup SPN and keytab files
This repo contains ansible playbooks and python helper code to enable the tasks we identified in my previous article (https://github.com/sjyang18/mydocs/blob/dev/accumulo-aad/wo_hdinsight/accumulo_aad_wo_hdinsight.md). The tasks we identified in that article before setting up Accumulo services are: 
1. Generate your organizational unit (OU) to hold new domain objects (computers, users, service principals) 
2. Join your cluster to your target AAD domain
3. Generate users and service principals and keytab files

As of now, it is in the proof-of-concept phase and tested these tasks with a generic Azure VMSS with no dependency on Accumulo. For simplicity, we first set up a VNET, setup peering to the VNET with AAD Domain Services, and provisioned a VMSS in that VNET. 

To run this playbook, login into a proxy VM that is shared with the same ssh user login and public key of the target VMSS. Then, git clone this repo and add a file called hosts with the following conten at the top. Replace with your values. Note that in the example below, we set 'accumulo' to a ldap_binddn value, which mean this user exists in my AAD and it is a member of `AAD DC Administrators`. You will be prompted for the password of this user during playbook execution.

```
[accumulomaster]
vmss25xip000000 short_hostname=m1

[workers]
vmss25xip000003 short_hostname=w1

[accumulo:children]
accumulomaster
workers

[all:vars]
ansible_python_interpreter=/usr/bin/python3
domain_name=xxxxx.onmicrosoft.com
realm_name={{ domain_name |upper }}
domain_dn=DC=xxxxx,DC=onmicrosoft,DC=com
domain_workgroup=XXXXX
custom_ou_name=MyCustomOU
ldap_host_ip_address=10.0.0.5
ldap_hostname=ldaps.xxxxx.onmicrosoft.com
ldap_uri=ldaps://{{ ldap_hostname }}
ldap_binddn='CN=accumulo,OU=AADDC Users,{{ domain_dn }}'
encoded_user_init_password=<<Replace with your encoded user passowrd (i.e. unicodePwd) >>
decoded_user_init_password=<<Replace with your user password chosen >>
```

Note that we also set short_hostname for each host. This short_hostname is used to generate sAMAccountName, which has the length limit, during user account generation thru ldap. 

Use lib/genEncodedPasswd.py to geneate your own encoded password. Original passowrd and encoded one would be used to create users and retrieve keytab files for spn mapped to those users.

Run the following sequence of ansible playbooks.

```
ansible-playbook -i hosts ansible/ldap_config.yml
ansible-playbook -i hosts ansible/ldap_addou.yml
ansible-playbook -i hosts ansible/join_domain.yml
ansible-playbook -i hosts ansible/retreive_keytab_file.yml
```






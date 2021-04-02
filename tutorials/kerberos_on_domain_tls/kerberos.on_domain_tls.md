# Enabling Kerberos on domain-enabled and TLS-enabled Accumulo cluster
Given you have enabled Domain and TLS in your Accumulo cluster (for example, in our previous tutorial, I employed Azure AAD Domain service for this purpose, and the tutorial is available in https://github.com/sjyang18/accumulo-w-aad/blob/main/tutorials/domain_plus_tls/domain.plus.tls.md), this time, we are going to add & modify kerberos-related configuration to the cluster. In general, this involves the two stages: 1) adding service principals and their keytab files to your selected domain/kerberos service, 2) adding & modifying hadoop and accumulo configuration for enabling kerberos with keytab files. Currently, we have multiple domain services & kerberos service products and different methodologies to setting up e& gnerating keytab files. To avoid the tightly-coupled solution, this tutorial will show one replacable first stage of generating keytab files from the same cluster environment we created in the previous tutorial, and demonstrate the second stage deployment with the expected keytabs file name patterns.  

## Stop Accumulo services, HDFS, and zookeeper services
Before we proceed, make sure to stop services from one of head nodes. Follow this order of shutting service.

```
accumulo-cluster stop
stop-dfs.sh

# and reboot Azure VMSS from portal to stop zookeepers and other hadoop services 
```


## Git clone this repo to get fluo-mucho addon ansible playbooks 
Inside the proxy/bastion node, run to get this repo. We used this repo in the previous tutorial to join accumulo cluster to Azure AAD domain service.

```
sudo yum install git
git clone https://github.com/sjyang18/accumulo-w-aad.git
```
You may copy out ~/ansible/conf/hosts generated by fluo-much to $HOME and add the requried variables to hosts file (The variables is mentioned in https://github.com/sjyang18/accumulo-w-aad/blob/main/tutorials/domain_plus_tls/domain.plus.tls.md#edit-ansible-inventory-file). This will save from losing these variables when you run 'mucho sync' command. Some of variables you may check again depending on your cluster are:
```
cluster_domain_name=domain_name
ldap_hostname=XXX
ldap_host_ip_address=ONE_OF_DNS_SERVER_ADDRESS_FROM_YOUR_DOMAIN_SERVER
custom_ou_name=XXX              # custom organization unit where you want to add users
domain_admin_username=XXX       # one of username who is Azure AAD domain
```

## Service principal and keytab files
In order to enable kerberos in Accumulo cluster with fluo-mucho, we need to first generate service principals and keytab files for those. If you have followed our previous tutorial and joined your cluster to Azure AAD domain services, customers may run the following command to generate users, the corresponding service principals, and keytab files.

```
ansible-playbook -i hosts accumulo-w-aad/ansible/ldap_adduser.yml
```

Otherwise, we expect customers to generate those service principals and corresponding keytab files with the following file name convention.

```
HTTP.{{ hostname }}.keytab
{{ service_user_name }}.{{ hostname }}.keytab
```

For example, 'ldap_adduser.yml' would generate the following keytab files for my cluster and fetch them to keytabs directory in bastion host.
```
[azureuser@bastion ~]$ tree keytabs/
keytabs/
├── azureuser.accucluster3-0.keytab
├── azureuser.accucluster3-1.keytab
├── azureuser.accucluster3-2.keytab
├── azureuser.accucluster3-3.keytab
├── azureuser.accucluster3-4.keytab
├── azureuser.accucluster3-5.keytab
├── azureuser.accucluster3-6.keytab
├── azureuser.accucluster3-8.keytab
├── HTTP.accucluster3-0.keytab
├── HTTP.accucluster3-1.keytab
├── HTTP.accucluster3-2.keytab
├── HTTP.accucluster3-3.keytab
├── HTTP.accucluster3-4.keytab
├── HTTP.accucluster3-5.keytab
├── HTTP.accucluster3-6.keytab
└── HTTP.accucluster3-8.keytab
```

By chance, if you see the following error, you might have to update the password of AAD DC Administrator user 'https://myaccount.microsoft.com/'. Log into the site with the user you choose for AAD DC Administrator user and update its password.

```
ldap_sasl_bind(SIMPLE): Can't contact LDAP server (-1)
```

## Switch off SSL in Accumulo
Comment out instance.rpc.ssl.enabled in accumulo.properties and ssl.enabled in accumulo-client.properties. We will enable instance.rpc.sasl for kerberos later. **Note that even we comment out these properties, we still have zookeeper.ssl.* JVM flags in `accumulo-env.sh`**

## Add Kerberos configuration in Hadoop and Accumulo
Deploy kerberos configuration to Hadoop and Accumulo with the following command.

```
ansible-playbook -i ~/hosts accumulo-w-aad/ansible/enable-kerberos.yml
```

If needed, you may override variable 'service_principal_login' and 'keytabs_pickup_dir' with -e switch. The default values for these variables are current user login in bastion host, and its ~/keytabs directory respectively.


## Administrative User
As mentioned in Accumulo user document (https://accumulo.apache.org/docs/2.x/security/kerberos#administrative-user), the Accumulo still has a single user 'root' with administrative permission. This has to change to authenticate with kerberos with 'accumulo init --reset-security' command. **Make sure that you stop accumulo services before resetting the administrative user.** Let's say you have accumulo_admin@EXAMPLE.COM as your admin. Before resetting admin, login in with your service principal user name (i.e. azureuser in my case) to Accumulo master/manager nodes, run kinit with your service principal and its keytab file. For example in my cluster,

```
kinit -r9d -kt /opt/muchos/install/keytabs/azureuser.keytab azureuser/accucluster3-1.example.com@EXAMPLE.COM
```

If you have multiple master/manager nodes, run kinit on other master/manager nodes too. Even though you have configured this service principal and its keytab file in accumulo.properties, my observation is that 'Accumulo init' process is picking up the kerberos authentication from the current login's key cache, and this key cache should be set on all master/manager during 'Accumulo init' process. Otherwise, you will see the 'Authentication' related error. 

Then, run 'accumulo init --reset-security' and give your admin user account and its password during the process.
```
$ accumulo init --reset-security
Running against secured HDFS
Principal (user) to grant administrative privileges to : acculumo_admin@EXAMPLE.COM
Enter initial password for accumulo_admin@EXAMPLE.COM (this may not be applicable for your security setup):
Confirm initial password for accumulo_admin@EXAMPLE.COM:
2021-03-31T22:18:11,900 [handler.KerberosAuthenticator] INFO : Removed /accumulo/f7bf7bd7-f823-479d-bc89-f887c5f99244/users/ from zookeeper
```

If it is ok to lose existing datta in accumulo, you could completely drop accumulo directory from HDFS and rerun 'accumulo init' without '--reset-security', which I did during troubleshooting.

```
hdfs dfs -rm -r /accumulo
accumulo init

OpenJDK 64-Bit Server VM warning: Option UseConcMarkSweepGC was deprecated in version 9.0 and will likely be removed in a future release.
2021-03-31T22:46:34,145 [conf.SiteConfiguration] INFO : Found Accumulo configuration on classpath at /opt/muchos/install/accumulo-2.1.0-SNAPSHOT/conf/accumulo.properties
2021-03-31T22:46:34,298 [security.SecurityUtil] INFO : Attempting to login with keytab as azureuser/accucluster3-0.example.onmicrosoft.com@EXAMPLE.ONMICROSOFT.COM
2021-03-31T22:46:35,437 [security.UserGroupInformation] INFO : Login successful for user azureuser/accucluster3-0.example.onmicrosoft.com@EXAMPLE.ONMICROSOFT.COM using keytab file /opt/muchos/install/keytabs/azureuser.keytab. Keytab auto renewal enabled : false
2021-03-31T22:46:35,438 [security.SecurityUtil] INFO : Succesfully logged in as user azureuser/accucluster3-0.example.onmicrosoft.com@EXAMPLE.ONMICROSOFT.COM
2021-03-31T22:46:36,028 [init.Initialize] INFO : Hadoop Filesystem is hdfs://accucluster3
2021-03-31T22:46:36,029 [init.Initialize] INFO : Accumulo data dirs are [[hdfs://accucluster3/accumulo]]
2021-03-31T22:46:36,029 [init.Initialize] INFO : Zookeeper server is accucluster3-0.example.onmicrosoft.com:2191,accucluster3-1.example.onmicrosoft.com:2191,accucluster3-2.example.onmicrosoft.com:2191
2021-03-31T22:46:36,030 [init.Initialize] INFO : Checking if Zookeeper is available. If this hangs, then you need to make sure zookeeper is running
Instance name : muchos
Instance name "muchos" exists. Delete existing entry from zookeeper? [Y/N] : Y
Running against secured HDFS
Principal (user) to grant administrative privileges to : accumulo@EXAMPLE.ONMICROSOFT.COM
2021-03-31T22:47:12,163 [Configuration.deprecation] INFO : dfs.replication.min is deprecated. Instead, use dfs.namenode.replication.min
2021-03-31T22:47:13,126 [Configuration.deprecation] INFO : dfs.block.size is deprecated. Instead, use dfs.blocksize
2021-03-31T22:47:13,171 [bcfile.Compression] INFO : Trying to load codec class org.apache.hadoop.io.compress.LzoCodec for io.compression.codec.lzo.class
2021-03-31T22:47:13,175 [bcfile.Compression] INFO : Trying to load codec class org.apache.hadoop.io.compress.SnappyCodec for io.compression.codec.snappy.class
2021-03-31T22:47:13,178 [bcfile.Compression] INFO : Trying to load codec class org.apache.hadoop.io.compress.ZStandardCodec for io.compression.codec.zstd.class
2021-03-31T22:47:13,194 [zlib.ZlibFactory] INFO : Successfully loaded & initialized native-zlib library
2021-03-31T22:47:13,195 [compress.CodecPool] INFO : Got brand-new compressor [.deflate]
```

## Start up services one by one
Start zookeepers, hadoop dfs services, and Accumulo. For example, in my cluster environment, I run the following commands on a head node.

```
# start zookeepers
zkServer.sh start
ssh accucluster3-1 "/opt/muchos/install/apache-zookeeper-3.5.9-bin/bin/zkServer.sh start"
ssh accucluster3-2 "/opt/muchos/install/apache-zookeeper-3.5.9-bin/bin/zkServer.sh start"

# start hadoop dfs services
start-dfs.sh

# start accumulo services
accumulo-cluster start

```

## Kerberos Verfication in Accumulo
Change your login to your admin. In my testing environment, 'accumulo' is the admin user name. We are verifying the admin user may create a table, insert data, flush data, and drop the table.

```
sudo su accumulo
```

Copy accumulo-client.properties into its home diretory and update auth.principal.
```
cd ~
cp /opt/muchos/install/accumulo-2.1.0-SNAPSHOT/conf/accumulo-client.properties ~/

## vi accumulo-client.properties
auth.principal=accumulo@EXAMPLE.ONMICROSOFT.COM
```

Run 'kinit' 
```
kdestroy
kinit -V accumulo@EXAMPLE.ONMICROSOFT.COM
# give passowrd to login and get kerberos key
```
Start accumulo shell with the new accumulo-client.properties. Note that 'ashell' command will start with the default accumulo-client.properties file, which is not what we want. 


```
 /opt/muchos/install/accumulo-2.1.0-SNAPSHOT/bin/accumulo shell --config-file ~/accumulo-client.properties
```
You should see the login prompt is your 
Run the basic operations to verify kerberos-based authentication and permission. Below, I captured the screenshot and blacked out the full domain name for security reason.  
```
[accumulo@example.onmicrosoft.com@accucluster3-0 ~]$ /opt/muchos/install/accumulo-2.1.0-SNAPSHOT/bin/accumulo shell --config-file ~/accumulo-client.properties
OpenJDK 64-Bit Server VM warning: Option UseConcMarkSweepGC was deprecated in version 9.0 and will likely be removed in a future release.

2021-03-31T22:54:58,429 [tracer.AsyncSpanReceiver] INFO : host from config: accucluster3-0
2021-03-31T22:54:58,429 [tracer.AsyncSpanReceiver] INFO : starting span receiver with hostname accucluster3-0

Shell - Apache Accumulo Interactive Shell
-
- version: 2.1.0-SNAPSHOT
- instance name: muchos
- instance id: 50706f09-c529-4433-8c6a-89a9d21795e1
-
- type 'help' for a list of available commands
-

accumulo@EXAMPLE.ONMICROSOFT.COM@muchos>
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos>
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos>
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos>
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos>
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos> users
azureuser/accucluster3-1.example.onmicrosoft.com@EXAMPLE.ONMICROSOFT.COM
azureuser/accucluster3-0.example.onmicrosoft.com@EXAMPLE.ONMICROSOFT.COM
accumulo@EXAMPLE.ONMICROSOFT.COM
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos>
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos>
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos>
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos> createtable test
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos test>
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos test> insert a b c d
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos test> flush -w
2021-03-31T22:55:42,000 [shell.Shell] INFO : Flush of table test  completed.
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos test>
accumulo@EXAMPLE.ONMICROSOFT.COM@muchos test> droptable test
droptable { test } (yes|no)? yes
Table: [test] has been deleted.

```

Do the same testing with another normal user account in Azure AD. You should see the permission error. Fix the permission error with the following from accumulo admin shell.

```
# before retesting, grant
grant System.CREATE_TABLE -s -u seyan@EXAMPLE.ONMICROSOFT.COM

# after testing, revoke 
#revoke System.CREATE_TABLE -s -u seyan@EXAMPLE.ONMICROSOFT.COM
```

And, this time, the normal user should be able to run basic operational tests without permission errors.

## Multiple ACL for delegation_token_keys and Workaround
I found that once accumulo-cluster stops and starts again, accumulo managers are crashing with the error throwing the message of multiple ACL entries for delegation_token_keys. The issue is filed as an issue (https://github.com/apache/accumulo/issues/1984). For now, the workaround is reset ACL to have one entry with digest:accumulo:*.

First, get the accumulo instance id from hdfs, then get the Acl of the instance with `getAcl`. The format of path is /accumulo/${accumulo_id}.
Note that you find the line with `'digest', 'accumulo:'`. 
Then, reset Acl for /accumulo/${accumulo_id}/delegation_token_keys with the digested accumulo account and the cdrwa permission.

```
[azureuser@accucluster3-0 conf]$ hdfs dfs -ls /accumulo
Found 4 items
drwxr-xr-x   - azureuser supergroup          0 2021-04-01 23:54 /accumulo/instance_id
drwxr-xr-x   - azureuser supergroup          0 2021-04-01 23:54 /accumulo/tables
drwx------   - azureuser supergroup          0 2021-04-01 23:54 /accumulo/version
drwx------   - azureuser supergroup          0 2021-04-02 00:04 /accumulo/wal
[azureuser@accucluster3-0 conf]$ hdfs dfs -ls /accumulo/instance_id
Found 1 items
-rw-r--r--   2 azureuser supergroup          0 2021-04-01 23:54 /accumulo/instance_id/00a5058f-9813-422a-9144-1ae6bf510dca
[azureuser@accucluster3-0 conf]$ zkCli.sh -server $(hostname -f):2191
Connecting to accucluster3-0.example.onmicrosoft.com:2191
Welcome to ZooKeeper!
JLine support is enabled
[zk: accucluster3-0.example.onmicrosoft.com:2191(CONNECTING) 0]
WATCHER::

WatchedEvent state:SyncConnected type:None path:null

WATCHER::

WatchedEvent state:SaslAuthenticated type:None path:null

[zk: accucluster3-0.example.onmicrosoft.com:2191(CONNECTED) 0] getAcl /accumulo/00a5058f-9813-422a-9144-1ae6bf510dca
'x509,'CN=accucluster3-0.example.onmicrosoft.com
: cdrwa
'sasl,'azureuser
: cdrwa
'digest,'accumulo:KBeh49allLP6OCuJmbGiQ7Q0guQ=
: cdrwa
'world,'anyone
: r
[zk: accucluster3-0.example.onmicrosoft.com:2191(CONNECTED) 1] setAcl /accumulo/00a5058f-9813-422a-9144-1ae6bf510dca/delegation_token_keys digest:accumulo:KBeh49allLP6OCuJmbGiQ7Q0guQ=:cdrwa

```






# Enable TLS by uploading Certificates signed by external or intermediate CA
This document captures the steps for the scenario where customer employs the third-party or intermediate CA for signing certficates and enabling TLS. In this case, we need customer to create JKS truststore.jks and host-keystore.jks files using signed certificates and key for each host, outside the cluster. Reference `openssl` and `keytool` commands for this pre-work are captured at the end of this document. Use this internal fluo-muchos patch (https://dev.azure.com/AZGlobal/AG%20E2E%5E2%20-%20Secure%20Data%20Estate/_git/fluo-muchos/pullrequest/2874) to push JKS files to your cluster.


## Upload keystore files to fluo-mucho bastion host
Once you create the keystore files from signed certificates and host keys, create a $HOME/certs directory and upload truststore.jks and host-keystore.jks files. 

```
[azureuser@bastion certs]$ ls -al
total 40
drwxrwxr-x.  2 azureuser azureuser  236 Mar 10 23:58 .
drwx------. 11 azureuser azureuser 4096 Mar 10 23:57 ..
-rw-rw-r--.  1 azureuser azureuser 2782 Mar 10 23:58 accucluster4-0.jks
-rw-rw-r--.  1 azureuser azureuser 2782 Mar 10 23:58 accucluster4-1.jks
-rw-rw-r--.  1 azureuser azureuser 2783 Mar 10 23:58 accucluster4-2.jks
-rw-rw-r--.  1 azureuser azureuser 2781 Mar 10 23:58 accucluster4-4.jks
-rw-rw-r--.  1 azureuser azureuser 2780 Mar 10 23:58 accucluster4-5.jks
-rw-rw-r--.  1 azureuser azureuser 2781 Mar 10 23:58 accucluster4-6.jks
-rw-rw-r--.  1 azureuser azureuser 2782 Mar 10 23:58 accucluster4-8.jks
-rw-rw-r--.  1 azureuser azureuser 2782 Mar 10 23:58 accucluster4-9.jks
-rw-rw-r--.  1 azureuser azureuser  830 Mar 10 23:58 truststore.jks
```

`truststore.jks` contains the CA's certificate that is used to sign other host key certificates. And, `host-keystore.jks` contains the certificate signed by your CA, and host key. Make sure that you are using the same keystore password value as tls_password value used in ansible-playbook.

```
[azureuser@bastion certs]$ keytool -list -keystore truststore.jks
Enter keystore password:
Keystore type: JKS
Keystore provider: SUN

Your keystore contains 1 entry

ca-key, Mar 10, 2021, trustedCertEntry,
Certificate fingerprint (SHA-256): C1:F0:14:68:F7:05:2E:12:83:DD:F0:60:D1:13:EC:57:62:0B:D6:43:5A:39:17:6A:27:EA:5E:30:4A:DF:62:7A

[azureuser@bastion certs]$ keytool -list -keystore accucluster4-0.jks
Enter keystore password:
Keystore type: JKS
Keystore provider: SUN

Your keystore contains 2 entries

accucluster4-0, Mar 10, 2021, PrivateKeyEntry,
Certificate fingerprint (SHA-256): 43:72:AA:59:0D:E7:1F:56:34:5F:26:F0:E4:68:44:9B:7F:F9:60:5C:D6:F4:6F:33:EC:22:DF:8A:DA:9C:B2:7B
accucluster4-0-crt, Mar 10, 2021, trustedCertEntry,
Certificate fingerprint (SHA-256): 43:72:AA:59:0D:E7:1F:56:34:5F:26:F0:E4:68:44:9B:7F:F9:60:5C:D6:F4:6F:33:EC:22:DF:8A:DA:9C:B2:7B
```

# Execute enable-tls.yml with additional variable
Disable self-signed CA and certificates with `'with_self_signed_ca=False'` and enable uploading certificates to you cluster with `'upload_signed_certs=True'`. The variable `certs_dir` should be pointing to the directory of keystore files in your bastion host.
```
ansible-playbook ansible/enable-tls.yml -i ansible/conf/hosts -e "tls_password=hadoop with_self_signed_ca=False upload_signed_certs=True certs_dir=/home/azureuser/certs"
```

# Reference commands to used to generate key and keystore for host-keystore.jks
```
# generate key
/usr/bin/openssl genrsa -passout pass:{{ tls_password }} -out $(hostname -f).key 2048
# generate a certificate request using key
/usr/bin/openssl req -new -key $(hostname -f).key -days 999 -out $(hostname -f).csr -subj="/CN=$(hostname -f)" -passin pass:{{ tls_password }}

# get signed certificate from your CA
#
# work with your chosen CA platform to CA.crt and host.crt for each host.
# Match the name of host as hostname of nodes in your accumulo host
# If your cluster is domain-joined, use the FQDN name for host-keystore file name.
#

# import CA.crt to truststore.jks
/usr/bin/keytool -import -noprompt -alias CA-key -file CA.crt -keystore truststore.jks -storepass {{ tls_password }} -storetype jks

# you get certificate in $(hostname -f).crt file and copy back to your working directory
/usr/bin/openssl pkcs12 -export -in $(hostname -f).crt -inkey $(hostname -f).key -certfile $(hostname -f).crt -name $(hostname) -out $(hostname).p12 -passin pass:{{ tls_password }} -passout pass:{{ tls_password }}
/usr/bin/keytool -importkeystore -srckeystore $(hostname).p12 -srcstoretype pkcs12 -destkeystore host-keystore.jks -deststoretype jks -srcstorepass {{ tls_password }} -storepass {{ tls_password }} -noprompt

```




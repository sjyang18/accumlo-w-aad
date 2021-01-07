# Enabling TLS on Hadoop

## Generate certifcates & keystores:
1. Run the below commands on each host & generate a ".crt" file per host. Change the default password with yours.
    ```
    export STORE_KEY_PASSWORD=hadoop
    mkdir -p $HADOOP_HOME/etc/hadoop/ssl
    keytool -genkeypair -alias $(hostname -f) -keyalg RSA -keysize 2048 -dname "cn=$(hostname -f)" -keypass $STORE_KEY_PASSWORD -keystore $HADOOP_HOME/etc/hadoop/ssl/host-keystore.jks -storepass $STORE_KEY_PASSWORD
    keytool -exportcert -alias $(hostname -f) -keystore $HADOOP_HOME/etc/hadoop/ssl/host-keystore.jks -file $HADOOP_HOME/etc/hadoop/ssl/$(hostname -f).crt -rfc -storepass $STORE_KEY_PASSWORD
    keytool -importcert -alias $(hostname -f) -file $HADOOP_HOME/etc/hadoop/ssl/$(hostname -f).crt -keystore $HADOOP_HOME/etc/hadoop/ssl/host-truststore.jks -storepass $STORE_KEY_PASSWORD -noprompt
    ```

2. Copy the '*.crt' file generated on each hosts to the first name node and generate the trusted.jsk as shown below.

    ```
    export STORE_KEY_PASSWORD=hadoop
    for i in `ls *.crt`; do
        name=$(echo $i | sed 's/\.crt//g')
        keytool -importcert -alias $name -file $name.crt -keystore truststore.jks -storepass $STORE_KEY_PASSWORD -noprompt
    done
    ```

3. Copy "truststore.jks" to all the hosts

    ```
    for i in `cat host_list`; do 
        scp truststore.jks $i:$HADOOP_HOME/etc/hadoop/ssl/; 
    done
    ```
## Hadoop Configuration changes
1. Stop all Hadoop daemons, if not already done.
    ```
    stop-dfs.sh
    ```

2. Add `hadoop.rpc.protection` property and its value to $HADOOP_HOME/etc/hadoop/core-site.xml
    ```
    <property>
        <name>hadoop.rpc.protection</name>
        <value>privacy</value>
    </property>
    ```

3. Add the following propertis to $HADOOP_HOME/etc/hadoop/hdfs-site.xml. Make sure to enable HTTPS_ONLY for `dfs.http.policy`.
    ```
    <property>
        <name>dfs.webhdfs.enabled</name>
        <value>true</value>
    </property>

    <property>
        <name>dfs.https.enable</name>
        <value>true</value>
    </property>

    <property>
        <name>dfs.http.policy</name>
        <value>HTTPS_ONLY</value>
    </property>

    <property>
        <name>dfs.encrypt.data.transfer</name>
        <value>true</value>
    </property>

    <property>
        <name>dfs.block.access.token.enable</name>
        <value>true</value>
    </property>

    <property>
        <name>dfs.datanode.https.address</name>
        <value>0.0.0.0:50075</value>
    </property>

    ## The below properties should already be set in muchos, just need to ensure ##

    <property>
        <name>dfs.namenode.https-address.accucluster.nn1</name>
        <value><host1>:50071</value>
    </property>
    
    <property>
        <name>dfs.namenode.https-address.accucluster.nn2</name>
        <value><host2>:50071</value>
    </property>
    ```

4. Add to $HADOOP_HOME/etc/hadoop/yarn-site.xml the following properties.

    ```
    <property>
        <name>yarn.http.policy</name>
        <value>HTTPS_ONLY</value>
    </property>

    <property>
        <name>yarn.resourcemanager.webapp.https.address</name>
        <value><RM host>:8089</value>
    </property>

    <property>
        <name>yarn.log.server.url</name>
        <value>https://<RM host>:19889/jobhistory/logs</value>
    </property>

    <property>
        <name>yarn.nodemanager.webapp.https.address</name>
        <value>0.0.0.0:8090</value>
    </property>
    ```

5. Add to $HADOOP_HOME/etc/hadoop/mapred-site.xml the following properties.
    ```
    <property>
        <name>yarn.http.policy</name>
        <value>HTTPS_ONLY</value>
    </property>

    <property>
        <name>yarn.resourcemanager.webapp.https.address</name>
        <value><RM host>:8089</value>
    </property>

    <property>
        <name>yarn.log.server.url</name>
        <value>https://<RM host>:19889/jobhistory/logs</value>
    </property>

    <property>
        <name>yarn.nodemanager.webapp.https.address</name>
        <value>0.0.0.0:8090</value>
    </property>
    ```

6. Create ssl-server.xml from the sample. Make sure to update the keystore and truststore's password with yours.
    ```
    <configuration>
    <property>
    <name>ssl.server.truststore.location</name>
    <value>/opt/muchos/install/hadoop-3.2.1/etc/hadoop/ssl/host-truststore.jks</value>
    <description>Truststore to be used by NN and DN. Must be specified.
    </description>
    </property>

    <property>
    <name>ssl.server.truststore.password</name>
    <value>hadoop</value>
    <description>Optional. Default value is "".
    </description>
    </property>

    <property>
    <name>ssl.server.truststore.type</name>
    <value>jks</value>
    <description>Optional. The keystore file format, default value is "jks".
    </description>
    </property>

    <property>
    <name>ssl.server.truststore.reload.interval</name>
    <value>10000</value>
    <description>Truststore reload check interval, in milliseconds.
    Default value is 10000 (10 seconds).
    </description>
    </property>

    <property>
    <name>ssl.server.keystore.location</name>
    <value>/opt/muchos/install/hadoop-3.2.1/etc/hadoop/ssl/host-keystore.jks</value>
    <description>Keystore to be used by NN and DN. Must be specified.
    </description>
    </property>

    <property>
    <name>ssl.server.keystore.password</name>
    <value>hadoop</value>
    <description>Must be specified.
    </description>  
    </property>

    <property>
    <name>ssl.server.keystore.keypassword</name>
    <value>hadoop</value>
    <description>Must be specified.
    </description>
    </property>

    <property>
    <name>ssl.server.keystore.type</name>
    <value>jks</value>
    <description>Optional. The keystore file format, default value is "jks".
    </description>
    </property>
    ```
7. Create ssl-client.xml and update the passwords.
    ```
    <configuration>
    <property>
    <name>ssl.client.truststore.location</name>
    <value>/opt/muchos/install/hadoop-3.2.1/etc/hadoop/ssl/truststore.jks</value>
    <description>Truststore to be used by clients like distcp. Must be specified.
    </description>
    </property>

    <property>
    <name>ssl.client.truststore.password</name>
    <value>hadoop</value>
    <description>Optional. Default value is "".
    </description>
    </property>

    <property>
    <name>ssl.client.truststore.type</name>
    <value>jks</value>
    <description>Optional. The keystore file format, default value is "jks".
    </description>
    </property>

    <property>
    <name>ssl.client.truststore.reload.interval</name>
    <value>10000</value>
    <description>Truststore reload check interval, in milliseconds.
    Default value is 10000 (10 seconds).
    </description>
    </property>

    <property>
    <name>ssl.client.keystore.location</name>
    <value></value>
    <description>Keystore to be used by clients like distcp. Must be specified.
    </description>
    </property>

    <property>
    <name>ssl.client.keystore.password</name>
    <value></value>
    <description>Optional. Default value is "".
    </description>
    </property>

    <property>
    <name>ssl.client.keystore.keypassword</name>
    <value></value>
    <description>Optional. Default value is "".
    </description>
    </property>

    <property>
    <name>ssl.client.keystore.type</name>
    <value>jks</value>
    <description>Optional. The keystore file format, default value is "jks".
    </description>
    </property>

    </configuration>
    ```

7. Copy the config files to all the hosts

    ```
    for i in `cat ~/host_list`; do scp /opt/muchos/install/hadoop-3.2.1/etc/hadoop/core-site.xml $i:/opt/muchos/install/hadoop-3.2.1/etc/hadoop/; done
    for i in `cat ~/host_list`; do scp /opt/muchos/install/hadoop-3.2.1/etc/hadoop/hdfs-site.xml $i:/opt/muchos/install/hadoop-3.2.1/etc/hadoop/; done
    for i in `cat ~/host_list`; do scp /opt/muchos/install/hadoop-3.2.1/etc/hadoop/yarn-site.xml $i:/opt/muchos/install/hadoop-3.2.1/etc/hadoop/; done
    for i in `cat ~/host_list`; do scp /opt/muchos/install/hadoop-3.2.1/etc/hadoop/mapred-site.xml $i:/opt/muchos/install/hadoop-3.2.1/etc/hadoop/; done
    for i in `cat ~/host_list`; do scp /opt/muchos/install/hadoop-3.2.1/etc/hadoop/ssl-server.xml $i:/opt/muchos/install/hadoop-3.2.1/etc/hadoop/; done
    for i in `cat ~/host_list`; do scp /opt/muchos/install/hadoop-3.2.1/etc/hadoop/ssl-client.xml $i:/opt/muchos/install/hadoop-3.2.1/etc/hadoop/; done
    ```

## Testing
1. Start Hadoop daemons and verifies all daemons are running without failure from the log files.

    ```
    start-dfs.sh
    jps -m
    #tail -f /var/data/data2/logs/hadoop/hadoop-XXX-namenode-XXX.log
    ```

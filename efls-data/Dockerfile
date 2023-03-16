ARG flink_version=1.13.6
FROM flink:${flink_version}
WORKDIR /xfl

RUN sed -i 's#http://deb.debian.org#https://mirrors.aliyun.com#g' /etc/apt/sources.list \
    && sed -i 's#http://security.debian.org#https://mirrors.aliyun.com#g' /etc/apt/sources.list \
    && echo 'deb http://mirrors.aliyun.com/debian-security stretch/updates main' >> /etc/apt/sources.list \
    && sed -i 's#echo gosu flink#echo gosu root#g; s#echo su-exec flink#echo su-exec root#g' /docker-entrypoint.sh \
    && apt-get -y update \
    && apt-get install -y default-libmysqlclient-dev vim procps zip\
    && apt-get -y install libgmp-dev \
    && apt-get -y install libmpfr-dev \
    && apt-get -y install libmpc-dev \
    && apt-get -y install libffi-dev libbz2-dev\
    && apt-get -y install openjdk-8-jdk \
    && apt-get -y install openssl libssl-dev cmake nasm git \
    && apt-get -y install  libpcre3 libpcre3-dev \
    && rm -rf /var/lib/apt/lists/*

ENV LD_LIBRARY_PATH=/usr/local/lib

#install python37
RUN  cd /opt \
    && wget https://mirrors.aliyun.com/macports/distfiles/python37/Python-3.7.10.tar.xz \
    && tar -xf Python-3.7.10.tar.xz && cd ./Python-3.7.10 && ./configure --enable-shared\
    && make -j8 && make -j8 altinstall \
    && ln -s /usr/local/bin/python3.7 /usr/local/bin/python \
    && rm -rf Python-3.7.10 Python-3.7.10.tar.xz

COPY . /xfl

RUN cd /xfl \
    && wget https://nginx.org/download/nginx-1.20.1.tar.gz \
    && tar -zxvf nginx-1.20.1.tar.gz && cd ./nginx-1.20.1 \
    &&./configure --with-http_gzip_static_module --with-http_ssl_module --with-http_stub_status_module --with-stream --with-http_v2_module \
    && make -j$(nproc) && make install \
    &&ln -s /usr/local/nginx/sbin/nginx /usr/local/bin/nginx

#Use IPPCP for crypto algorithm with avx512-ifma

#ENV LD_LIBRARY_PATH=/opt/intel/ippcp/lib/intel64
#ENV LIBRARY_PATH=/opt/intel/ippcp/lib/intel64
#RUN cd /xfl/third_party/ipp-crypto \
#    && cmake . -DARCH=intel64 -DCMAKE_INSTALL_PREFIX=/opt/intel/ippcp \
#    && make -j$(nproc) && make install \
#    && cd /xfl && mkdir build && cd build && cmake .. && make -j$(nproc)

ARG flink_version=1.13.6
RUN cd /xfl/xfl-java \
    && wget https://mirrors.aliyun.com/apache/maven/maven-3/3.2.5/binaries/apache-maven-3.2.5-bin.tar.gz \
    && tar -zxvf apache-maven-3.2.5-bin.tar.gz \
    && export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64 \
    && ./apache-maven-3.2.5/bin/mvn clean package \
    && cp /xfl/xfl-java/target/efls-flink-connectors-1.0-SNAPSHOT.jar /opt/flink/lib/ \
    && mkdir -p /xfl/lib/ \
    && cp /xfl/xfl-java/target/efls-flink-connectors-1.0-SNAPSHOT.jar /xfl/lib/ \
    && cp /opt/flink/opt/flink-oss-fs-hadoop-${flink_version}.jar /opt/flink/lib/ \
    && zip -d /opt/flink/lib/flink-oss-fs-hadoop-${flink_version}.jar org/apache/flink/fs/osshadoop/common/HadoopRecoverableWriter.class \
    && zip -d /opt/flink/lib/flink-dist_2.12-${flink_version}.jar org/apache/flink/streaming/runtime/partitioner/KeyGroupStreamPartitioner.class \
    && rm -rf ~/.m2 \
    && rm -rf apache-maven-3.2.5* \
	  && apt-get -y remove openjdk-8-jdk \
    && echo "fs.oss.endpoint: endpointnotrequired" >> /opt/flink/conf/flink-conf.yaml \
    && echo "fs.oss.accessKeyId: aknotrequired" >> /opt/flink/conf/flink-conf.yaml \
    && echo "fs.oss.accessKeySecret: sknotrequired" >> /opt/flink/conf/flink-conf.yaml
#We fix flink's bug on OSSFileSystem in HadoopRecoverableWriter.class
#We modify KeyGroupStreamPartitioner.class to ensure that currentKey of data in the subtask is equal to subtask_index

RUN cd /xfl/third_party/curve25519 \
    && python setup.py install

RUN python -m pip install -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --upgrade pip \
    && python -m pip install -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt --default-timeout=1000 --no-cache-dir future \
    && rm -rf ~/.cache/pip

RUN cd /xfl \
    && python -m grpc_tools.protoc -I . --python_out=. ./xfl/data/tfreecord/tfrecords.proto \
    && python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./proto/*.proto

RUN apt-get autoremove -y

ENV PYTHONPATH=/xfl:$PYTHONPATH
ENV TZ="Asia/Shanghai"

CMD []


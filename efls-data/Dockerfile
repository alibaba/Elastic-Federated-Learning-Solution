FROM flink:1.13.1-java8
WORKDIR /xfl

RUN sed -i 's#http://deb.debian.org#https://mirrors.aliyun.com#g' /etc/apt/sources.list \
    && echo 'deb http://mirrors.aliyun.com/debian-security stretch/updates main' >> /etc/apt/sources.list \
    && sed -i 's#echo gosu flink#echo gosu root#g; s#echo su-exec flink#echo su-exec root#g' /docker-entrypoint.sh \
    && apt-get -y update \
    && apt-get install -y python3.7 python3-pip python3.7-dev default-libmysqlclient-dev vim procps zip\
    && apt-get -y install libgmp-dev \
    && apt-get -y install libmpfr-dev \
    && apt-get -y install libmpc-dev \
    && apt-get -y install openjdk-8-jdk \
    && apt-get -y install openssl libssl-dev cmake nasm git \
    && apt-get -y install  libpcre3 libpcre3-dev \
    && rm -rf /var/lib/apt/lists/*

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

RUN cd /xfl/xfl-java \
    && wget -q https://archive.apache.org/dist/maven/maven-3/3.2.5/binaries/apache-maven-3.2.5-bin.tar.gz \
    && tar -zxvf apache-maven-3.2.5-bin.tar.gz \
    && export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64 \
    && ./apache-maven-3.2.5/bin/mvn clean package \
    && cp /xfl/xfl-java/target/efls-flink-connectors-1.0-SNAPSHOT.jar /opt/flink/lib/ \
    && mkdir -p /xfl/lib/ \
    && cp /xfl/xfl-java/target/efls-flink-connectors-1.0-SNAPSHOT.jar /xfl/lib/ \
    && cp /opt/flink/opt/flink-oss-fs-hadoop-1.13.1.jar /opt/flink/lib/ \
    && zip -d /opt/flink/lib/flink-oss-fs-hadoop-1.13.1.jar org/apache/flink/fs/osshadoop/common/HadoopRecoverableWriter.class \
    && zip -d /opt/flink/lib/flink-dist_2.12-1.13.1.jar org/apache/flink/streaming/runtime/partitioner/KeyGroupStreamPartitioner.class \
    && rm -rf ~/.m2 \
    && rm -rf apache-maven-3.2.5* \
    && apt-get -y remove openjdk-8-jdk
#We fix flink's bug on OSSFileSystem in HadoopRecoverableWriter.class
#We modify KeyGroupStreamPartitioner.class to ensure that currentKey of data in the subtask is equal to subtask_index

RUN ln -s /usr/bin/python3 /usr/bin/python

RUN cd /xfl/third_party/curve25519 \
    && python setup.py install

RUN python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip \
    && python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt --default-timeout=1000 --no-cache-dir future \
    && rm -rf ~/.cache/pip

RUN cd /xfl \
    && python -m grpc_tools.protoc -I . --python_out=. ./xfl/data/tfreecord/tfrecords.proto \
    && python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. ./proto/*.proto

RUN apt-get autoremove -y

ENV PYTHONPATH=/xfl:$PYTHONPATH
ENV TZ="Asia/Shanghai"

CMD []


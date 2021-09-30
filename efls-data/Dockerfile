FROM flink:1.13.1-java8
WORKDIR /xfl

COPY . /xfl

RUN sed -i 's#http://deb.debian.org#https://mirrors.aliyun.com#g' /etc/apt/sources.list \
    && echo 'deb http://mirrors.aliyun.com/debian-security stretch/updates main' >> /etc/apt/sources.list \
    && sed -i 's#echo gosu flink#echo gosu root#g; s#echo su-exec flink#echo su-exec root#g' /docker-entrypoint.sh \
    && apt-get -y update \
    && apt-get install -y python3.7 python3-pip python3.7-dev default-libmysqlclient-dev vim procps zip\
    && apt-get -y install libgmp-dev \
    && apt-get -y install libmpfr-dev \
    && apt-get -y install libmpc-dev \
    && rm -rf /var/lib/apt/lists/*

RUN cp /xfl/lib/efls-flink-connectors-1.0-SNAPSHOT.jar /opt/flink/lib/ \
    && cp /opt/flink/opt/flink-oss-fs-hadoop-1.13.1.jar /opt/flink/lib/ \
    && zip -d /opt/flink/lib/flink-oss-fs-hadoop-1.13.1.jar org/apache/flink/fs/osshadoop/common/HadoopRecoverableWriter.class \
    && zip -d /opt/flink/lib/flink-dist_2.12-1.13.1.jar org/apache/flink/streaming/runtime/partitioner/KeyGroupStreamPartitioner.class
#We fix flink's bug on OSSFileSystem in HadoopRecoverableWriter.class
#We modify KeyGroupStreamPartitioner.class to ensure that currentKey of data in the subtask is equal to subtask_index

RUN ln -s /usr/bin/python3 /usr/bin/python

RUN python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip \
    && python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt --default-timeout=1000 --no-cache-dir future \
    && rm -rf ~/.cache/pip

ENV PYTHONPATH=/xfl:$PYTHONPATH
ENV TZ="Asia/Shanghai"

CMD []



FROM node:14.17.6 as build

ARG STATIC_ARG
ENV STATIC=$STATIC_ARG

WORKDIR /src
ADD ["front_end/", "./"]
RUN yarn config set registry https://registry.npm.taobao.org/ && yarn
RUN  npm run build 

FROM centos
LABEL MAINTAINER=hongfu.phf@alibaba-inc.com description="elastic federated learning solution"

ARG ENV_ARG
ARG EXPOSE_ARG
ENV ENV=$ENV_ARG
ENV PORT=$EXPOSE_ARG
ENV SERVICE_HOME=/alifl/console

RUN yum clean all \
    && touch /var/lib/rpm/* \
    && yum install -y python3-devel \
    && yum install -y python3-pip 
    
COPY ./ $SERVICE_HOME/

COPY  --from=build ./src/dist $SERVICE_HOME/static/
COPY  --from=build ./src/dist/index.html $SERVICE_HOME/templates/index.html

RUN pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple/ --upgrade pip \
    && pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r $SERVICE_HOME/requirements.txt

WORKDIR $SERVICE_HOME

EXPOSE $PORT

CMD ["bash", "start.sh"]

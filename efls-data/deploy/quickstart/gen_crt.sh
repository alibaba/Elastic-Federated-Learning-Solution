DOMAIN_NAME="alifl.alibaba-inc.com"
openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 -keyout tls.key -out tls.crt -subj "/CN=${DOMAIN_NAME}/O=${DOMAIN_NAME}"
kubectl create secret tls tls-secret --key tls.key --cert tls.crt

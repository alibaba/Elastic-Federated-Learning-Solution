DOMAIN_NAME="*.alifl.alibaba-inc.com"
openssl req -x509 -sha256 -nodes -days 365 -newkey rsa:2048 -keyout trainer.key -out trainer.crt -subj "/CN=${DOMAIN_NAME}"
kubectl create secret tls efl-trainer --key trainer.key --cert trainer.crt

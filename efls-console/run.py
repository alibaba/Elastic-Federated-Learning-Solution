# -*- coding: utf8 -*-

from console.core import create_app
from console.constant import SERVICE_HOST, SERVICE_PORT, SERVICE_DEBUG

app = create_app()
if __name__ == '__main__':
    app.run(host=app.config[SERVICE_HOST], port=app.config[SERVICE_PORT], debug=app.config[SERVICE_DEBUG])

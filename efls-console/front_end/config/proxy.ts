/**
 * 在生产环境 代理是无法生效的，所以这里没有生产环境的配置
 * -------------------------------
 * The agent cannot take effect in the production environment
 * so there is no configuration of the production environment
 * For details, please see
 * https://pro.ant.design/docs/deploy
 */

const hostIp = 'http://100.82.84.137:31000';
const peerIp = 'http://100.82.84.137:31001';
const proxyIp = hostIp; 
// const proxyIp = peerIp; 

export default {
  dev: {
    '/user': {
      target: proxyIp,
      changeOrigin: true,
      pathRewrite: { '^': '' },
    },
    '/project': {
      target: proxyIp,
      changeOrigin: true,
      pathRewrite: { '^': '' },
    },
    '/task': {
      target: proxyIp,
      changeOrigin: true,
      pathRewrite: { '^': '' },
    },
    '/instance': {
      target: proxyIp,
      changeOrigin: true,
      pathRewrite: { '^': '' },
    },
    '/resource': {
      target: proxyIp,
      changeOrigin: true,
      pathRewrite: { '^': '' },
    },
  },
  test: {
    '/api/': {
      target: 'https://preview.pro.ant.design',
      changeOrigin: true,
      pathRewrite: { '^': '' },
    },
  },
  pre: {
    '/api/': {
      target: 'your pre url',
      changeOrigin: true,
      pathRewrite: { '^': '' },
    },
  },
};

// https://umijs.org/config/
import { defineConfig } from 'umi';
import { join } from 'path';

import defaultSettings from './defaultSettings';
import proxy from './proxy';
import routes from './routes';
import webpackPlugin from './plugin.config';

const { REACT_APP_ENV } = process.env;

export default defineConfig({
  hash: true,
  publicPath: !!process.env.STATIC ? `/${process.env.STATIC}/` : '/',
  define: {
    flaskStatic: process.env.STATIC,
  },
  history:{type:"hash"},
  antd: {},
  dva: {
    hmr: true,
  },
  devtool:'source-map',
  layout: {
    // https://umijs.org/zh-CN/plugins/plugin-layout
    locale: true,
    siderWidth: 208,
    ...defaultSettings,
  },
  // https://umijs.org/zh-CN/plugins/plugin-locale
  locale: {
    // default zh-CN
    default: 'zh-CN',
    antd: true,
    // default true, when it is true, will use `navigator.language` overwrite default
    baseNavigator: true,
  },
  dynamicImport: {
    loading: '@ant-design/pro-layout/es/PageLoading',
  },
  targets: {
    ie: 11,
  },
  // umi routes: https://umijs.org/docs/routing
  routes,
  // Theme for antd: https://ant.design/docs/react/customize-theme-cn
  theme: {
    'primary-color': defaultSettings.primaryColor,
  },
  // esbuild is father build tools
  // https://umijs.org/plugins/plugin-esbuild
  esbuild: {},
  title: false,
  ignoreMomentLocale: true,
  proxy: proxy[REACT_APP_ENV || 'dev'],
  manifest: {
    basePath: '/',
  },
  // Fast Refresh 热更新
  fastRefresh: {},
  openAPI: false,
  nodeModulesTransform: { type: 'none' },
  mfsu: false,
  webpack5: {},
  exportStatic: {},
  inlineLimit:30000,
  chainWebpack: webpackPlugin,

});

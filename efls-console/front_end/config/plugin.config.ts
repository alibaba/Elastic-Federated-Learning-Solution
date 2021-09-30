import * as IWebpackChainConfig from 'webpack-chain';
import MonacoWebpackPlugin from 'monaco-editor-webpack-plugin';
// const MonacoWebpackPlugin = require('monaco-editor-webpack-plugin');

const webpackPlugin = (config: IWebpackChainConfig) => {
  config.plugin('monaco-editor-webpack-plugin').use(MonacoWebpackPlugin, [
    {
      languages: ['json', 'python', 'xml', 'yaml'],
    },
  ]);
  console.log('webpack Config', config.toConfig());
  console.log('webpack jsonString',JSON.stringify(config.toConfig()));
  return config;
};

export default webpackPlugin;


// import MonacoWebpackPlugin from 'monaco-editor-webpack-plugin';

// export default {
//   chainWebpack: (memo:IWebpackChainConfig) => {
//     // 更多配置 https://github.com/Microsoft/monaco-editor-webpack-plugin#options
//     memo.plugin('monaco-editor-webpack-plugin').use(MonacoWebpackPlugin, [
//       // 按需配置
//       { languages: ['javascript'] }
//     ]);
//     console.log('webpack Config', memo.toConfig());
//     console.log('webpack jsonString',JSON.stringify(memo.toConfig()));
//     return memo;
//   }
// }
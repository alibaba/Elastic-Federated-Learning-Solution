Language : 🇺🇸 | [🇨🇳](./README.zh-CN.md) | [🇷🇺](./README.ru-RU.md) | [🇹🇷](./README.tr-TR.md) | [🇯🇵](./README.ja-JP.md) | [🇫🇷](./README.fr-FR.md) | [🇵🇹](./README.pt-BR.md) | [🇸🇦](./README.ar-DZ.md)

<h1 align="center">Elastic-Federated-Learning-Platform</h1>

<div align="center">

A web-based UI for the Elastic-Federated-Learning.
</div>

### 功能点
* 项目管理
* 数据任务管理
* 训练任务管理

### Use bash

```bash

$ yarn install
$ npm start         # visit http://localhost:8000
# with mock
$ npm run start:mock
```
本地开发模式单独启动UI,需修改 `config/proxy.ts` proxyIp为正确web-console地址.

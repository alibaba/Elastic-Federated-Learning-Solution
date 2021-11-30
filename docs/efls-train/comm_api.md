# Communicator
Communicator是联邦学习训练框架中联邦双方互相通信的接口，基于gRPC异步接口实现，默认采用非安全的传输方式，但为用户提供了使用SSL保证传输安全的选项。
​

通信协议可在`protos/trainer_service.proto`中查看。协议共包含四类报文：

- `ConnectionRequest`与`ConnectionResponse`用于双方创建连接。
- `MessageRequest`与`MessageResponse`用于双方发送Tensor。
- `GetReaderStateRequest`与`GetReaderStateResponse`用于双方协商当前训练的TFRecord文件名。
- `GetCheckpointVersionRequest`与`GetCheckpointVersionResponse`用于双方协商检查点。



各类报文的功能实现都被封装为op，用户通过调用Communicator的不同方法创建并获取相应的op。
​

在Kernel中，Communicator拥有三个重要的成员，你需要了解它们的作用：

- **Server**：监听端口，接收对方发来的请求，判断请求类型，执行相应逻辑并向对方返回响应。
- **Client**：向对方发送请求，接收来自对方的响应，判断响应类型并执行相应逻辑。
- **Monitor**: 注册Communicator创建的op，每隔一定时间扫描注册的op，检查其执行时间是否超时，超时则会抛出`tensorflow::errors::DeadlineExceeded`错误。



与C/S架构不同，联邦双方都要互相发送请求和响应，所以无论是follower还是leader，Communicator中都既有Server也有Client，二者并不分离。
​

可以通过设置以下环境变量来采用SSL的传输方式：

| **Client要使用的环境变量** |  |
| --- | --- |
| **EFL_PEER_CERTS_FILENAME** | 对方的证书文件路径及文件名 |
| **EFL_SSL_TARGET_NAME_OVERRIDE** | 当对方的hostname与CN域名不一致时，需要将该环境变量设置为CN的域名 |
| **Server要使用的环境变量** |  |
| **EFL_MY_CERTS_FILENAME** | 我方的证书文件路径及文件名 |
| **EFL_MY_KEY_FILENAME** | 我方的密钥文件路径及文件名 |
| **EFL_PEER_CERTS_FILENAME** | 对方的证书文件路径及文件名 |

注意：在k8s的ingress-nginx通信模式下，只需要client开启SSL，server侧无需开启SSL模式。其他情况下双方的SSL需要同时开启和关闭。只有`EFL_MY_CERTS_FILENAME`和`EFL_MY_KEY_FILENAME`都存在时Server才会开启SSL选项；只有`EFL_PEER_CERTS_FILENAME`存在时，Client才会开启SSL选项。
​

可以通过以下环境变量设置报文大小范围：

| **EFL_CLIENT_MAX_SEND_MESSAGE_SIZE** | Client发送的报文大小的最大值，单位字节。 |
| --- | --- |
| **EFL_CLIENT_MAX_RECEIVE_MESSAGE_SIZE** | Client接收的报文大小的最大值，单位字节。 |
| **EFL_SERVER_MAX_SEND_MESSAGE_SIZE** | Server发送的报文大小的最大值，单位字节。 |
| **EFL_SERVER_MAX_RECEIVE_MESSAGE_SIZE** | Server接收的报文大小的最大值，单位字节。 |

```python
efl.Communicator(
    federal_role, peer_addr, local_addr,
    client_thread_num=None, server_thread_num=None,
    scanning_interval_milliseconds=None, default_timeout_milliseconds=None
)
```
# 参数
| **​参数列表** |  |  |
| --- | --- | --- |
| **federal_role** | `string` | 当前参与方在联邦学习任务中扮演的角色。有`'follower'`和`'leader'`两个选项。 |
| **peer_addr** | `string` | 对方的IP地址及端口。 |
| **local_addr** | `string` | 我方的IP地址及端口。 |
| **client_thread_num** | `int` | Client线程数，默认为1。 |
| **server_thread_num** | `int` | Server线程数，默认为1。 |
| **scanning_interval_milliseconds** | `int` | Monitor扫描间隔，单位毫秒，默认为30秒。 |
| **default_timeout_milliseconds** | `int` | Monitor超时阈值，单位毫秒，默认为10分钟。 |

# 属性
| **属性列表** |  |  |
| --- | --- | --- |
| **hook** | `CommunicatorHook` | 定义了创建session前后和训练前后communicator的行为。 |

# 方法
## send
```python
send(
    name, tensor
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **name** | `string` | 用于在双方通信时唯一标识一个Tensor。 |
| **tensor** | `tf.Tensor` | 要发送的Tensor。 |
| **功能及返回值** |  |  |
| `op` |  | 返回一个发送Tensor的op。 |

## recv
```python
recv(
    name, dtype=tf.float32
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **name** | `string` | 用于在双方通信时唯一标识一个Tensor。 |
| **dtype** | `tf.dtypes.Dtype` | 接收的Tensor类型。 |
| **功能及返回值** |  |  |
| `op` |  | 返回一个接收Tensor的op。op的输出时接收到的tensor。 |

## send_ckpt_version
```python
send_ckpt_version(
    sess, version
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **sess** | `tf.Session` | 要发送checkpoint version的会话。 |
| **version** | `string` | 要发送的checkpoint version。 |
| **功能及返回值** |  |  |
| `None` |  | 在会话`sess`中执行一个向对方发送检查点版本`version`的op。该方法一般由leader调用。无返回值。 |

## recv_ckpt_version
```python
recv_ckpt_version(
    sess
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **sess** | `tf.Session` | 要接收checkpoint version的会话。 |
| **功能及返回值** |  |  |
| `string` |  | 在会话`sess`中执行一个接收检查点版本的op。该方法一般由follower调用。返回接受的`version`。 |

## send_reader_state
```python
send_reader_state(
    name, block_id, sample_index
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **name** | `string` | 数据集的名字。框架支持双方训练多个数据集，因此对于每一个数据集双方必须填写相同的名字才能顺利通信。 |
| **block_id** | `string` | 每个数据集会被切分成多个block，`block_id`标识当前要读取的block。 |
| **sample_index** | `string` | 当前要读取的起始样本在block中的偏移。 |
| **功能及返回值** |  |  |
| `op` |  | 该方法返回一个发送数据集读取状态的op，一般由leader调用。 |

## recv_reader_state
```python
recv_reader_state(
    name
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **name** | `string` | 数据集的名字。框架支持双方训练多个数据集，因此对于每一个数据集双方必须填写相同的名字才能顺利通信。 |
| **功能及返回值** |  |  |
| `op` |  | 该方法返回一个接收数据集读取状态的op，op的输出是一个元组`(block_id, sample_index)`。因为每个数据集会被切分成多个block，`block_id`标识当前要读取的block，`sample_index`是当前要读取的起始样本在block中的偏移。该方法一般由follower调用。 |

## initialize
```python
initializer(
    sess
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **sess** | `tf.Session` | 要接收checkpoint version的会话。 |
| **功能及返回值** |  |  |
| `None` |  | 在会话`sess`中执行初始化当前的Communicator的op，应该在所有涉及收发Tensor和ReaderState的op都创建完后调用。CommunicatorHook在创建session后会调用该方法。无返回值。 |

## shutdown
```python
shutdown(
    sess
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **sess** | `tf.Session` | 要接收checkpoint version的会话。 |
| **功能及返回值** |  |  |
| `None` |  | 在会话`sess`中执行关闭当前的Communicator的op，一个Communicator关闭后不能再次使用。CommunicatorHook在session结束后会调用该方法。无返回值。 |

## terminate_reader
```python
terminate_reader(
    name
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **name** | `string` | 要结束读取的数据集的名字。 |
| **功能及返回值** |  |  |
| `op` |  | 该方法返回一个结束数据读取的op，一般由leader调用，用于通知follower训练完毕。 |

## add_step
```python
add_step()
```
| **功能及返回值** |  |  |
| --- | --- | --- |
| `None` |  | 该方法返回一个对训练步数加1的op。CommunicatorHook在每一步训练结束后会调用该方法。无返回值。 |

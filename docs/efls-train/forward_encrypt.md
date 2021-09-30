# 算法简介
前向加密参考论文：[Additively Homomorphical Encryption based Deep Neural Network for Asymmetrically Collaborative Machine Learning](https://arxiv.org/pdf/2007.06849.pdf)<br />
EFLS实现了一个用来做前向加密的加密层，用来将一侧联邦计算方的embedding发送到另一方，完成两侧embedding的合并操作。该算法通过同态加密和加噪的方式对于前向和后向交互的embedding数据来说，接收方仅能得到一个加密的数据或者加噪的数据，并且无法还原数据本来的信息，以达到加密的效果。具体的算法流程可以参考引用的论文。<br />
# EncryptLayer
## EncryptPassiveLayer
一般由leader侧创建，接收follower侧发送的加密embedding，和自己提供的embedding合并起来，并乘以一个权重。
```python
efl.privacy.EncryptPassiveLayer
```
### 参数
| **​参数列表** |  |  |
| --- | --- | --- |
| **communicator** | `efl.Communicator` | 用于数据交互的通信器 |
| **dim** | `int` | 己方提供的embedding维度 |
| **recv_dim** | `int` | 接收对方的embedding维度 |
| **public_file** | `string` | 公钥所在文件地址 |
| **learning_rate** | `float` | 内部variable的学习率 |
| **initializer** | `tf.Initializer` | 权重初始化器，默认为全1的初始化器 |
| **name** | `string` | 该层的名字 |

### 方法
### __call__
```python
layer(inputs)
```
| **参数​** |  |  |
| --- | --- | --- |
| **inputs** | `tf.Tensor` | 己方提供的embedding |
| **功能及返回值** |  |  |
| `tf.Tensor` |  | 己方提供的embedding和对方发送的embeeding合并(concat)后，乘以随机初始化权重的结果 |

## EncryptActiveLayer
一般由follower侧创建，向leader侧发送的加密embedding。
```python
efl.privacy.EncryptActiveLayer
```
### 参数
| **​参数列表** |  |  |
| --- | --- | --- |
| **communicator** | `efl.Communicator` | 用于数据交互的通信器 |
| **dim** | `int` | 己方提供的embedding维度 |
| **public_file** | `string` | 公钥所在文件地址 |
| **private_file** | `string` | 私钥所在文件地址 |
| **learning_rate** | `float` | 内部variable的学习率 |
| **noise_initializer** | `tf.Initializer` | 噪声初始化器，默认为全0的初始化器 |
| **update_noise** | `bool` | 是否在训练过程中迭代改变噪声 |
| **name** | `string` | 该层的名字 |

### 方法
### __call__
```python
layer(inputs)
```
| **参数​** |  |  |
| --- | --- | --- |
| **inputs** | `tf.Tensor` | 需要发送给对方的embedding |
| **功能及返回值** |  |  |
| `tf.Tensor` |  | 需要发送的embedding，值和inputs相同 |


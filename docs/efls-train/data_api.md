# DataIO
用于训练文件的读取。
```python
efl.data.DataIO(
    data_base_dir, batch_size, worker_idx, worker_num, prefetch=1,
    num_epochs=1, save_interval=100, drop_remainder=False, name='dataio'
)
```
## 参数
| **​参数列表** |  |  |
| --- | --- | --- |
| **data_base_dir** | `string` | 数据集的根目录。 |
| **batch_size** | `int` | batch大小。 |
| **worker_idx** | `int` | 当前worker的id。 |
| **worker_num** | `int` | 总worker数量。 |
| **prefetch** | `int` | 预取的样本数量。 |
| **num_epochs** | `int` | epoch数量。 |
| **save_interval** | `int` | 每训练`save_interval`步，保存一次序列化后的reader state。reader state由block id和sample index两部分组成，前者指定读取的block文件，后者指定读取的起始样本在该block文件中的偏移。 |
| **drop_remainer** | `bool` | `False`表示丢弃最后一个不满的batch，`True`则保留。 |
| **name** | `string` | 该`DataIO`的名字。 |

## 方法
### add_file_node
```python
add_file_node(
    file_node
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **file_node** | `string` | `data_base_dir`下的子目录。 |
| **功能及返回值** |  |  |
| `None` |  | `DataIO`新增一个准备读取的文件所在的子目录。若不指定，则读取全部子目录下的文件。无返回值。 |

### add_file_nodes
```python
add_file_nodes(
    file_nodes
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **file_nodes** | `list` | 包含若干`data_base_dir`下子目录的列表。 |
| **功能及返回值** |  |  |
| `None` |  | `DataIO`新增若干准备读取的文件所在的子目录。若不指定，则读取全部子目录下的文件。无返回值。 |

### fixedlen_feature
```python
fixedlen_feature(
    name, dim, dtype=tf.float32
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **name** | `string` | 该定长特征在TFRecord存储中对应的名字。 |
| **dim** | `int` | 该定长特征对应tensor中的元素个数。 |
| **dtype** | `tf.dtypes.Dtype` | 该定长特征的数据类型。 |
| **功能及返回值** |  |  |
| `None` |  | 定义一个定长的特征。无返回值。 |

### varlen_feature
```python
varlen_feature(
    name, dtype=tf.int64
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **name** | `string` | 该变长特征在TFRecord存储中对应的名字。 |
| **dtype** | `tf.dtypes.Dtype` | 该变长特征的数据类型。 |
| **功能及返回值** |  |  |
| `None` |  | 定义一个变长特征。无返回值。 |

### restore_from_reader_state_op
```python
restore_from_reader_state_op(
    reader_state
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **reader_state** | `string` | reader state序列化后的字符串。 |
| **功能及返回值** |  |  |
| `op` |  | 返回一个根据`reader_state`加载checkpoint的`op`。 |

### read
```python
read()
```
| **功能及返回值** |  |  |
| --- | --- | --- |
| `dict` |  | 获取一个batch的训练数据。key为特征名，value为特征对应的数据。 |

### init_dataset
```python
init_dataset()
```
| **功能及返回值** |  |  |
| --- | --- | --- |
| `tf.data.Dataset` |  | 初始化dataset，返回一个`tf.data.Dataset`。 |

### initialize_iter
```python
initialize_iter(
    sess
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **sess** | `tf.Session` | 一个tf会话。 |
| **功能及返回值** |  |  |
| `None` |  | 在`sess`中运行一个初始化DataIO迭代器的op。无返回值。 |

### get_hook
```python
get_hook()
```
| **功能及返回值** |  |  |
| --- | --- | --- |
| `DataIOHook` |  | 获取该`DataIO`对应的Hook。 |

# FederalDataIO
`efl.FederalDataIO`继承自`efl.DataIO`。用于联邦学习中训练文件的读取。
```python
efl.data.DataIO(
    data_base_dir, batch_size, communicator, role, worker_idx, worker_num,
    prefetch=1, num_epochs=1, save_interval=100, drop_remainder=False,
    data_mode='data-join', name='dataio'
)
```
## 参数
| **​参数列表** |  |  |
| --- | --- | --- |
| **data_base_dir** | `string` | 数据集的根目录。 |
| **batch_size** | `int` | batch大小。 |
| **communicator** | `efl.Communicator` | 联邦学习中双方通信用到的`Communicator`。 |
| **role** | `string` | 联邦学习角色，有`'follower'`和`'leader'`。 |
| **worker_idx** | `int` | 当前worker的id。 |
| **worker_num** | `int` | 总worker数量。 |
| **prefetch** | `int` | 预取的样本数量。 |
| **num_epochs** | `int` | epoch数量。 |
| **save_interval** | `int` | 每训练`save_interval`步，保存一次序列化后的reader state。reader state由block id和sample index两部分组成，前者指定读取的block文件，后者指定读取的起始样本在该block文件中的偏移。 |
| **drop_remainer** | `bool` | `False`表示丢弃最后一个不满的batch，`True`则保留。 |
| **data_mode** | `string` | 有`local`和`data-join`两个选项。当你使用我们联邦学习框架中的数据求交框架生成数据时，请使用`data-join`选项。当你使用自己生成的本地数据时，请使用`local`选项。需要注意，若使用本地生成的数据，follower与leader双方的文件名必须一致。 |
| **name** | `string` | 该`FederalDataIO`的名字。 |

## 方法
与`efl.DataIO`相比无新增方法。
# Sample
```python
efl.Sample(
    features, columns
)
```
## 参数
| **​参数列表** |  |  |
| --- | --- | --- |
| **features** | `dict` | 样本原始数据，key是特征名，value是该特征名对应的数据。 |
| **columns** | `dict` | `features`经过转换后的模型输入数据，key是列名，value是该列对应的`tf.feature_column`列表。
`columns`定义了`features`将以何种组织形式输入到模型中。 |

比如现在存在如下数据：

| 姓名 | 年龄 | 国籍 | 性别 |
| --- | --- | --- | --- |
| 张三 | 20 | 中国 | 男 |
| Alice | 20 | 美国 | 女 |

我们希望利用姓名，年龄和国籍判断一个人的性别，那么就可以如下定义`features`：
```python
features = {
  'name': tf.constant(['张三', 'Alice'], dtype=tf.string),
  'age': tf.constant([20, 20], dtype=tf.int64),
  'nationality': tf.constant(['中国', '美国'], dtype=tf.string)，
  'gender': tf.constant([1, 0], dtype=tf.int64)
}
```
如果你希望每个batch训练的数据不同，那么可以使用`tf.Dataset`或框架中提供的`efl.DataIO`。
输入的`features`将在`Sample`中根据`columns`的定义做相应的处理。`columns`的value是一个列表，这就意味着你可以将数据中的多个特征组合成一个特征列，根据`features`可以如下定义`columns`：
```python
columns = {
  'dense': [tf.feature_column.numeric_column('name', 1)],
  'embedding': [
    tf.feature_column.embedding_column(
      tf.feature_column.categorical_column_with_identity('name', 1000000),
        dimension=10, combiner='mean'),
    tf.feature_column.embedding_column(
      tf.feature_column.categorical_column_with_identity('nationality', 200),
        dimension=10, combiner='mean')]
  'label': [tf.feature_column.numeric_column('gender', 1)]
}
```
注意：在你定义`tf.feature_column`时，传入的`key`应与`features`的key对应。
```python
sample = efl.Sample(features, columns)
```
如此上述数据在`Sample`中就将组织为如下形式：

| dense | embedding | label |
| --- | --- | --- |
| 20 | `tf.Tensor(shape=[20,])` | 1 |
| 20 | `tf.Tensor(shape=[20,])` | 0 |

通过`sample['dense']`的方式就可以取出转换后的数据，然后即可将其输入到模型中。
## 属性
| **属性列表** |  |  |
| --- | --- | --- |
| **features** | `dict` | 样本原始数据。 |

## 方法
### to_dict
```python
to_dict()
```
| **功能及返回值** |  |  |
| --- | --- | --- |
| `dict` |  | 以字典的方式取出`features`经`columns`转换后的数据。 |

### create
```python
create(
    fgrps
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **fgrps** | `dict` | key是列名，value是列对应的数据。 |
| **功能及返回值** |  |  |
| `efl.Sample` |  | 该方法将返回一个根据当前`Sample`拷贝创建的新`Sample`，并利用`fgrpc`替换新`Sample`中转换后的数据。 |

### set_transformed_feature_groups
```python
set_transformed_feature_groups(
    fgrps
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **fgrps** | `dict` | key是列名，value是列对应的数据。 |
| **功能及返回值** |  |  |
| `None` |  | 该方法将用`fgrps`直接替换`efl.Sample`中通过`features`导入并由`columns`转换后生成的数据。无返回值。 |

### items
```python
items()
```
| **功能及返回值** |  |  |
| --- | --- | --- |
| `list` |  | 该方法等价于`to_dict().items()`。 |

### before_step_ops
```python
before_step_ops()
```
| **功能及返回值** |  |  |
| --- | --- | --- |
| `list` |  | 返回在开始每个step的训练前需要运行的所有`op`。 |

# FederalSample
`FederalSample`继承自`Sample`。
```python
efl.FederalSample(
    features, columns, federal_role, communicator,
    sample_id_name=None, verify_id=True, name='sample'
)
```
## 参数
| **​参数列表** |  |  |
| --- | --- | --- |
| **features** | `dict` | 样本数据，key是特征名，value是该特征名对应的数据。 |
| **columns** | `dict` | 模型输入数据，key是列名，value是该列对应的`tf.feature_column`列表。`columns`定义了`features`将以何种组织形式输入到模型中。 |
| **federal_role** | `string` | 在联邦学习中扮演的角色，有`'follower'`和`'leader'`。 |
| **communicator** | `efl.Communicator` | 联邦双方通信使用的`Communicator`。 |
| **sample_id_name** | `string` | `sample_id`对应的原始数据中的特征名。 |
| **verify_id** | `bool` | 是否校验联邦双方样本的`sample_id`一致性。 |
| **name** | `string` | 该`FederalSample`的名字。 |

注意：若`verify_id=True`，则原始数据`features`中需要有一个特征表示`sample_id`，该特征在双方构造的`FederalSample`中都应存在且一致。
## 属性
| **属性列表** |  |  |
| --- | --- | --- |
| **features** | `dict` | 样本原始数据。 |

## 方法
### verify_sample_id
```python
verify_sample_id()
```
| **功能及返回值** |  |  |
| --- | --- | --- |
| `op` |  | 返回一个检查联邦双方数据sample_id一致性的op。 |

# FederalDataset
`efl.data.FederalDataset`继承自`tf.data.Dataset`。
```python
efl.data.FederalDataset(
    filenames, block_ids=None, sample_index=0,
    compression_type='', buffer_size=256 * 1024
)
```
## 参数
| **​参数列表** |  |  |
| --- | --- | --- |
| **filenames** | `tf.Tensor` | `string`类型的`Tensor`，该数据集包含的所有文件名包含路径。 |
| **block_ids** | `tf.Tensor` | `string`类型的`Tensor`，该数据集包含的所有block文件。若为`None`则等于`filenames`。 |
| **sample_index** | `int` | 起始block中起始样本对应的偏移量。 |
| **compression_type** | `string` | 数据中`string`类型数据的压缩格式。`''`表示无压缩，`'ZLIB'`和`'GZIP'`分别代表两种压缩格式。 |
| **buffer_size** | `int` | 读缓冲区的大小，单位字节。0表示无缓冲区。 |

## 方法
与`tf.data.Dataset`相比无新增方法。

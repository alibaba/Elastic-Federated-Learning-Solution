# TaskScope
我们的训练框架支持多任务学习，因此使用`TaskScope`唯一标识一个训练任务。
```python
efl.framework.task_scope.TaskScope(
    mode=None, task=None
)
```
## 属性
| **属性列表​** |  |  |
| --- | --- | --- |
| **mode** | `efl.MODE` | 标识任务是否是训练任务。有`efl.MODE.TRAIN`和`efl.MODE.EVAL`两种选项。 |
| **task** | `string` | 任务名。 |

框架提供了两个接口：
`efl.task_scope`用于设定当前的`TaskScope`。
`efl.current_task_scope`用于获取当前的`TaskScope`。
# task_scope
```python
efl.task_scope(mode=None, task=None)
```
| **参数​** |  |  |
| --- | --- | --- |
| **mode** | `efl.MODE` | 标识当前任务是否是训练任务。
有`efl.MODE.TRAIN`和`efl.MODE.EVAL`两种选项。 |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `None` |  | 无返回值，根据`mode`和`task`创建并设定当前的`TaskScope`。 |

# current_task_scope
```python
efl.current_task_scope()
```
| **功能及返回值** |  |  |
| --- | --- | --- |
| `TaskScope` |  | 返回当前的`TaskScope`。 |

# Model
`Model`可以看作是整个训练模型的抽象，用户使用该训练框架大部分情况下就是在调用`Model`的各个api。
`Model`封装了模型各个任务使用的input、loss、model、metric、train_op、eval_op等。
```python
efl.Model()
```
## 属性
| **属性列表** |  |  |
| --- | --- | --- |
| **training_flag** | `tf.placeholder (tf.bool, shape=[])` | 训练时为`True`，否则为`False`。 |
| **global_step** | `tf.Tensor` | 模型的全局训练步数。 |
| **input_fns** | `dict` | 存储各任务的input function。 |
| **loss_fns** | `dict` | 存储各任务的loss function。 |
| **opt_fns** | `dict` | 存储各任务的optimizer。 |
| **losses** | `dict` | 存储各任务的loss operator。 |
| **inputs** | `dict` | 存储各任务输入的`efl.Sample`。 |
| **train_ops** | `dict` | 存储各训练任务的op。 |
| **extra_data** | `dict` | 存储用户自定义的额外数据。 |
| **metric_variables_initializer** | `op` | 初始化所有metric的op。 |
| **stage_mgr** | `StageManager` | 用于控制模型的训练过程。 |

## 方法
### input
```python
input(
    mode=MODE.TRAIN, task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **mode** | `efl.MODE` | 标识当前任务是否是训练任务。有`efl.MODE.TRAIN`和`efl.MODE.EVAL`两种选项。 |
|**task** | `string`   | 任务名，当只有一个任务时可以用`None`。                       |
| **功能及返回值** |            |                                                              |
| `efl.Sample`     |            | 根据传入的`mode`和`task`确定一个`TaskScope`，返回该`TaskScope`所代表的task的input。 |

### metrics
```python
metrics(
    mode=MODE.TRAIN, task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **mode** | `efl.MODE` | 标识当前任务是否是训练任务。有`efl.MODE.TRAIN`和`efl.MODE.EVAL`两种选项。 |
|**task** | `string`   | 任务名，当只有一个任务时可以用`None`。                       |
| **功能及返回值** |            |                                                              |
| `dict`           |            | 根据传入的`mode`和`task`确定一个`TaskScope`，返回该`TaskScope`所代表的task的metrics字典。key为name，value为对应的metric operator。 |

### add_extra_data
```python
add_extra_data(
    key, value
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **key** | `any` | 要添加的额外数据的key值。 |
| **value** | `any` | 要添加的额外数据。 |
| **功能及返回值** |  |  |
| `None` |  | 向模型中添加自定义的额外数据，无返回值。 |

### get_extra_data
```python
get_extra_data(
    key
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **key** | `any` | 要获取的额外数据的key值。 |
| **功能及返回值** |  |  |
| `any` |  | 返回`key`值对应数据。 |

### add_train_op
```python
add_train_op(
    train_op, task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **train_op** | `op` | 要添加的训练任务op。 |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `None` |  | 向模型中添加一个训练任务，无返回值。 |

### add_eval_op
```python
add_eval_op(
    eval_op, task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **eval_op** | `op` | 要添加的非训练任务op。 |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `None` |  | 向模型中添加一个非训练任务，无返回值。 |

### loss
```python
loss(
    task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `op` |  | 返回任务名为`task`对应的任务的loss_op。 |

### train_op
```python
train_op(
    task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `op` |  | 返回名为`task`的训练任务的op。 |

### eval_op
```python
eval_op(
    task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `op` |  | 返回名为`task`的非训练任务的op。 |

### opt_to_vars
```python
opt_to_vars(
    task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `dict` |  | 返回名为`task`的训练任务中optimizer及可训练变量的对应关系。key为optimizer，value是一个元组(vars, scope)。详情可见：[optimizer_fn](#BuClO)。 |

### add_hooks
```python
add_hooks(
    hooks, mode=MODE.TRAIN, task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **hooks** | `list` | 包含所有要添加的`tf.train.SessionRunHook`。 |
| **mode** | `efl.MODE` | 标识当前任务是否是训练任务。有`efl.MODE.TRAIN`和`efl.MODE.EVAL`两种选项。 |
|**task** | `string`   | 任务名，当只有一个任务时可以用`None`。                       |
| **功能及返回值** |            |                                                              |
| `None`           |            | 根据传入的`mode`和`task`确定一个`TaskScope`，向该`TaskScope`对应的任务中添加`hooks`中所有的`tf.train.SessionRunHook`。无返回值。 |

### add_metric
```python
add_metric(
    name, metric, mode=MODE.TRAIN, task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **name** | `string` | 要添加的metric名。 |
| **metric** | `op` | 要添加的metric对应的operator。 |
| **mode** | `efl.MODE` | 标识当前任务是否是训练任务。有`efl.MODE.TRAIN`和`efl.MODE.EVAL`两种选项。 |
|**task** | `string`   | 任务名，当只有一个任务时可以用`None`。                       |
| **功能及返回值** |            |                                                              |
| `None`           |            | 根据传入的`mode`和`task`确定一个`TaskScope`，向该`TaskScope`对应的任务中添加一个名为`name`的`metric`。无返回值。 |

### input_fn
```python
input_fn(
    input_fn, task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **input_fn** | `function` | 一个参数为`(efl.Model, efl.MODE)`，返回值为`efl.Sample`的函数，第一个参数用来传入模型，第二个参数用来指定任务类型，返回的是模型输入的数据。可参考示例程序。 |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `efl.Model` |  | 将名为`task`的任务的输入函数设置为`input_fn`，返回`Model`自身。 |

### loss_fn
```python
loss_fn(
    loss_fn, task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **loss_fn** | `function` | 一个参数为`(efl.Model, efl.Sample)`，返回值为`op`的函数。第一个参数用来传入模型，第二个参数用来传入输入数据，返回计算loss的op。可参考示例程序。 |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `efl.Model` |  | 将名为`task`的任务的损失函数设置为`loss_fn`，返回`Model`自身。 |

### optimizer_fn
```python
optimizer_fn(
    optimizer_fn, task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **optimizer_fn** | `function` | 一个参数为`(efl.Model, string)`，返回值为`dict`的函数。第一个参数用来传入模型，第二个参数表示任务名，返回值类似`opt_to_vars`接口的返回值。一般无需用户自定义，采用`efl.optimizer_fn`中的`optimzier_setter`接口生成，可参考示例程序。 |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `efl.Model` |  | 将名为`task`的任务的优化器函数设置为`optimizer_fn`，返回`Model`自身。 |

### eval_fn
```python
eval_fn(
    eval_fn, task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **eval_fn** | `function` | 一个参数为`(efl.Model, efl.Sample)`的函数。返回值是`None`或`op`。第一个参数用来传入模型，第二个参数用来传入输入数据，若有计算评估指标的`op`，返回该`op`。可参考示例程序。 |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `efl.Model` |  | 将名为`task`的任务的评估函数设置为`eval_fn`，返回`Model`自身。 |

### run_stage
我们将模型的整个训练过程抽象为一个个阶段(stage)，方便模型异常终止时从某一个阶段恢复模型。模型一次完整的训练过程就是在运行一个个stage。
```python
run_stage(
    name, stage_or_func, *args, **kwargs
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **name** | `string` | 对运行的stage命名。 |
|**stage_or_func**| `efl.Stage`或`function` | 要运行的函数或`efl.Stage`。 |
| **功能及返回值** |  |  |
| `None` |  | 运行一个`efl.Stage`或`function`，无返回值。 |

### compile
```python
compile(
    **kwargs
)
```
在`kwargs`中存在一些控制模型运行行为的参数：

| **参数​** |  |  |
| --- | --- | --- |
| **session_config** | `tf.ConfigProto` | 包含用户定义的选项，配置session的运算方式。 |
| **sync_optimizer_config** | `dict` | 用于配置`tf.train.SyncReplicasOptimizer`，在同步训练中使用。 |
| **opt_config** | `dict` | 用于配置差分隐私优化器，该选项默认值为：`{'REDUCE': 'mean','BACKEND_MODE': 'noise'}`。 |
| **功能及返回值**          |                  |                                                              |
| `efl.Model`               |                  | 编译计算图，返回`Model`自身。                                |

差分隐私优化器将batch又拆分成了一个个小batch，对每个小batch求loss，因此这就需要我们在给optimizer传入loss的时候，需要传入每个样本的loss，而不是传入所有样本loss的均值。optimizer内部会自行将这些样本分组。`opt_config`中的`REDUCE`选项就是在控制对于分组后的每个小batch，你希望如何合并小batch中每个样本的loss。`REDUCE='mean'`则使用`tf.reduce_mean`，`REDUCE='sum'`则使用`tf.reduce_sum`，`REDUCE`也可以是用户自定义的函数，该函数参数是一组loss，返回一个合并后的loss。函数形如：
```python
def reduce_func(loss):
    # do reduce
    return reduce_loss
```
差分隐私中需要对计算出的模型参数的梯度加入噪声。因此如果对方发送给我方的tensor是模型的参数时，计算出的梯度需要加入噪声；如果对方发送给我方的tensor是模型某一层的输出时，计算出的梯度不需要加入噪声。框架并不知道对方发送过来的tensor是哪种类型。`BACKEND_MODE`选项用于指定是否对回传的梯度加入噪声。`BACKEND_MODE='noise'`时加噪，`BACKEND_MODE='unnoise'`时不加噪。
### fit
```python
fit(
    procedure_fn, log_step = 100, project_name = "default_prj", **kwargs
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **procedure_fn** | `function` | 一个定义了模型完整训练过程的函数。详情可见：[procedure_fn](#uLHUf)。 |
| **log_step** | `int` | 模型每训练`log_step`步，打印一次日志。 |
| **project_name** | `string` | 为当前运行的训练项目命名。 |
| **checkpoint_dir** | `string` | 模型地址，如果地址存在则加载模型。 |
| **功能及返回值** |  |  |
| `None` |  | 启动模型的训练过程，无返回值。 |

# FederalModel
`FederalModel`继承自`Model`。是联邦学习中整个模型的抽象与封装。
```python
efl.FederalModel()
```
## 属性
除包含了`Model`的全部属性外，还有以下属性：

| **属性列表** |  |  |
| --- | --- | --- |
| **recv_grad_ops** | `dict` | 存储各任务创建的`require_grad=True`的recv_op。 |
| **require_grad_ops** | `dict` | 存储各任务的send_op对应的接收梯度的recv_op，这些op在调用send方法时由`Model`自行创建。 |
| **federal_role** | `string` | 我方在联邦学习中扮演的角色，有`'leader'`和`'follower'`两种。 |
| **communicator** | `efl.Communicator` | 用于和联邦学习的对方通信。 |

## 方法
除包含了`Model`的全部方法外，新增以下方法：
### send
```python
send(
    name, tensor, require_grad=False, mode=MODE.TRAIN, task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **name** | `string` | 用于在通信阶段唯一标识模型中的一个`Tensor`。 |
| **tensor** | `tf.Tensor` | 发送给对方的`Tensor`。 |
| **require_grad** | `bool` | `True`表示需要对方在训练后回传该`Tensor`对应的梯度。`False`则表示不需要。 |
| **mode** | `efl.MODE` | 标识当前任务是否是训练任务。有`efl.MODE.TRAIN`和`efl.MODE.EVAL`两种选项。 |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `op` |  | 返回一个发送tensor的op。该tensor由`mode`和`task`唯一确定的任务发送。 |

### recv
```python
recv(
    name, dtype=tf.float32, require_grad=False, task=None
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **name** | `string` | 用于在通信阶段唯一标识模型中的一个`Tensor`。 |
| **dtype** | `tf.dtypes.DType` | 接收的tensor类型。 |
| **require_grad** | `bool` | `True`表示我方应在训练后向对方回传该`Tensor`对应的梯度。`False`则表示不需要。 |
| **task** | `string` | 任务名，当只有一个任务时可以用`None`。 |
| **功能及返回值** |  |  |
| `op` |  | 返回一个发送tensor的op。该tensor由名为`task`的任务接收。 |

# optimizer_fn
我们的框架支持对模型中的不同变量使用不同的optimizer，通过把变量设置在不同的scope下，分别对不同的scope使用不同的optimizer的方式实现。因此我们的`Model`不能直接传入optimizer，而是要传入一些特定的函数来辅助框架完成这个机制，这些特定函数的返回值就是不同的optimizer与vars和scope的对应关系。我们提供了以下api来辅助用户创建这些特定的函数：
### optimzier_setter
当模型不需要多个optimizer时，可以调用`optimizer_setter`。
```python
efl.optimizer_fn.optimizer_setter(
    opt
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **opt** | `tf.Optimizer` | 训练时希望使用的optimizer。 |
| **功能及返回值** |  |  |
| `function` |  | 用于传给`efl.Model`的optimizer_fn。 |

### scope_optimizer
当你希望模型有多个optimizer时，调用`scope_optimizer`。
```python
efl.optimizer_fn.scope_optimizer(
    scope_to_opt
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **scope_to_opt** | `dict` | key是不同的scope，value是该scope中的变量要使用的optimizer。 |
| **功能及返回值** |  |  |
| `function` |  | 用于传给`efl.Model`的optimizer_fn。 |

# procedure_fn
在这里我们提供了一系列函数用于定义模型的执行过程，`Model.fit`接口中需要传入这里定义的函数。当然，你可以根据需求自定义模型执行函数。
### train
当你的模型只需要执行训练时，调用该接口。
```python
efl.procedure_fn.train(
    *args, **kwargs
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **max_step** | `int` | 训练步数。默认值为`None`，训练将持续到数据被消费完为止。 |
| **功能及返回值** |  |  |
| `function` |  | 返回一个定义了模型执行过程的函数。该函数的作用可以理解为模型执行了`max_step`次`loss_fn`，若数据提前消费完毕，则提前停止。 |

### eval
当你的模型只需要执行测试时，调用该接口。
```python
efl.procedure_fn.eval(
    *args, **kwargs
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **max_step** | `int` | 测试步数。默认值为`None`，测试将持续到数据被消费完为止。 |
| **功能及返回值** |  |  |
| `function` |  | 返回一个定义了模型执行过程的函数。该函数的作用可以理解为模型执行了`max_step`次`eval_fn`，若数据提前消费完毕，则提前停止。 |

### train_and_eval
当你的模型既训练又测试时，调用该接口。
```python
efl.procedure_fn.train_and_eval(
    *args, **kwargs
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **train_step** | `int` | 训练步数。默认值为None，训练将持续到数据被消费完为止。 |
| **eval_step** | `int` | 测试步数。默认值为None，测试将持续到数据被消费完为止。 |
| **train_interval** | `float` | 默认值为`None`。当`train_interval`非空，且每次迭代模型训练时间超过`train_interval`时，当前训练迭代提前终止。 |
| **eval_interval** | `float` | 默认值为`None`。当`eval_interval`非空，且每次迭代模型测试时间超过`eval_interval`时，当前测试迭代提前终止。 |
| **max_iter** | `int` | 迭代次数，即epochs。 |
| **功能及返回值** |  |  |
| `function` |  | 返回一个定义了模型执行过程的函数。该函数的作用可以理解为模型执行了`max_iter`次迭代，每次迭代执行`train_step`次训练和`eval_step`次测试，若数据提前消费完毕，则提前停止。 |

### cotrain
在多任务训练中可以调用该接口。每次训练将随机选取一个task更新模型。
```python
efl.procedure_fn.cotrain(
    *args, **kwargs
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **train_step** | `int` | 训练步数。默认值为None，训练将持续到数据被消费完为止。 |
| **eval_step** | `int` | 测试步数。默认值为None，测试将持续到数据被消费完为止。 |
| **max_iter** | `int` | 迭代次数，即epochs。 |
| **task_select_ratio** | `dict` | 该字典的key为任务名，value为该任务的ratio，每次训练会从所有的任务中随机挑选一个进行训练，概率由ratio决定。 |
| **功能及返回值** |  |  |
| `function` |  | 返回一个定义了模型执行过程的函数。该函数的作用可以理解为模型执行了`max_iter`次迭代，每次迭代执行`train_step`次训练和`eval_step`次测试，若数据提前消费完毕，则提前停止。 |

# Stage
为了让模型在failover时能够有效恢复，我们的框架使用了Stage作为模型训练各阶段的抽象。模型每次迭代中的训练和测试都被称为一个Stage。
Stage是一个callable的抽象接口，调用该接口时将执行它的`run`方法。
比如一个`procedure_fn.train_and_eval`模型在实际运行时，你可以简单理解为：
```python
for i in range(max_iter):
    model.run_stage(train_stage)
    model.run_stage(eval_stage)
```
```python
efl.Stage()
```
## 属性
| **属性列表** |  |  |
| --- | --- | --- |
| **sess** | `tf.Session` | 执行该`Stage`的会话。 |

## 方法
### run
```python
run(
    *args, **kwargs
)
```
注意：Stage接口并未实现该函数，继承他的子类需要实现该函数。
# LoopStage
`LoopStage`是`Stage`的实现类。正如其名，`LoopStage`的`run`方法内部实现了一个死循环，它的作用就是不断读取数据用于训练或测试，直至数据消耗完毕。
```python
efl.stage.LoopStage()
```
## 属性
| **属性列表** |  |  |
| --- | --- | --- |
| **sess** | `tf.Session` | 执行该`Stage`的会话。 |
| **finish** | `bool` | 初始化为`False`，当`LoopStage`捕获到`tf.errors.OutOfRangeError`或`StopIteration`时，或者`sess`的`should_stop`方法返回`True`时，finish为`True`，表示该`LoopStage`终止循环。 |

## 方法
### run
```python
run(
    feed_dict={}
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **feed_dict** | `dict` | 该参数将被传入`LoopStage`的`sess`中。 |
| **功能及返回值** |  |  |
| `None` |  | 无返回值。该方法执行时会不断消费数据，直至数据消费完毕。但模型每次迭代步数可能有限，不会消费完所有数据，当一次迭代完毕时，`LoopStage`会“挂起”该循环，暂时停止，保存循环步数。当数据消费完毕时，`finish`置为`True`，该循环真正停止。 |

# ModelBank
`ModelBank`是`Stage`的另一个实现类。
```python
efl.stage.ModelBank(
    is_chief, config=None
)
```
## 参数
| **参数列表** |  |  |
| --- | --- | --- |
| **is_chief** | `bool` | 是否是第0号worker。 |
| **config** | `dict` | 用于配制`ModelBank`。 |

## 属性
| **属性列表** |  |  |
| --- | --- | --- |
| **sess** | `tf.Session` | 执行该`Stage`的会话。 |

## config配置详解
Model bank的config配置是一个dict或list格式，其中的每一个元组都是一个需要加载的checkpoint来源和其配置，配置中必须有load exclude 和 path三个keyword，分别表示需要加载的variable/不需要加载的variable/模型地址。如果是dict，key表示的名字可以任意给定，只要不重复即可。如果使用list，则排在后面的model_bank中的ckpt里的变量，会覆盖掉排在前面的ckpt里面相同的变量，如果配置里恰好出现重复加载变量的情况。
### 示例一
从./ckpt/0 中加载variable a 和 b
```python
config['ckpt0'] = {'load': ['a', 'b'], 'exclude':[], 'path': './ckpt/0'}
```
### 示例二
从./ckpt/0 中加载所有在当前graph中存在的variable
```python
config['ckpt0'] = {'load': ['*'], 'exclude':[], 'path': './ckpt/0'}
```
### 示例三
从./ckpt/0 中加载符合"*/biases"不符合"a/*"名称的，在当前graph中存在的variable
```python
config['ckpt0'] = {'load': ['*/biases'], 'exclude':['a/*'], 'path': './ckpt/0'}
```
### 示例四
将./ckpt/0 中的名为'mlm_leaf/leafid'的variable加载到当前graph的'ad/leaf_id/leafid'中（如果当前graph中存在该variable）
```python
config['ckpt0'] = {'load': {'mlm_leaf/leafid': 'ad/leaf_id/leafid'}, 'exclude':[], 'path': './ckpt/0'}
```
## 方法
### run
```python
run()
```
| **功能及返回值** |  |  |
| --- | --- | --- |
| `None` |  | 无返回值。 |

# StageManager
根据配置文件中的信息，`Model`会自行创建所需的`StageManager`，该接口一般情况下无需关心。
```python
efl.framework.StageManager(
    root_scope, device, worker_id, worker_num, project_name, name
)
```
## 参数
| **参数列表** |  |  |
| --- | --- | --- |
|**root_scope**| `tf.VariabelScope`或`string` | `StageManager`会在`root_scope`下继续创建scope，`root_scope`是最上层的`scope`。 |
| **device** | `string` | 运行设备。 |
| **worker_id** | `int` | 该worker的编号。 |
| **worker_num** | `int` | worker总数。 |
| **project_name** | `string` | 项目名称。 |
| **name** | `string` | `StageManager名称。` |

## 方法
### init_arg
```python
init_arg(
    sess
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **sess** | `tf.Session` | 运行该`StageManager`的会话。 |
| **功能及返回值** |  |  |
| `None` |  | 无返回值。调用该方法将在`sess`中初始化`StageManager`需要的一些参数。 |

### set_monitored_sess
```python
set_monitored_sess(
    sess
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **sess** | `tf.Session` | 一个`tf.train.MonitoredSession`。 |
| **功能及返回值** |  |  |
| `None` |  | 设置一个`tf.train.MonitoredSession`，无返回值。 |

### stage
```python
stage(
    name, func, interval, *args, **kwargs
)
```
| **参数​** |  |  |
| --- | --- | --- |
| **name** | `string` | 要运行的`Stage`名。 |
|**func**| `function`或`efl.Stage` | 要运行的`Stage`。 |
| **interval** | `float` | 分布式场景下提前结束的worker的等待时间间隔。 |
| **功能及返回值** |  |  |
| `any` |  | 运行一个`Stage`，并返回结果。 |


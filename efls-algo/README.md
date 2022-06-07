# 模型介绍

## 水平聚合模型
我们提出基于水平聚合的特征融合方法，将媒体侧特征向量与电商侧特征通过门控机制进行水平方向融合。我们将电商侧用户、广告、场景Embedding，与媒体侧发送过来的特征向量通过多层感知机计算门控值，然后加权求和计算得到融合后的特征向量。通过上述融合方式，令模型从底层就接收媒体侧的特征表示，提升预估结果。

## 层次聚合模型
我们提出基于层次聚合的特征融合方法，不同于水平聚合仅利用媒体侧模型最上层的隐层向量，在层次聚合方法中我们将媒体侧中间层特征向量层次化地聚合连接到电商侧预估模型中，以提升我们模型的特征学习能力。由于聚合连接的组合方式随着网络层数增长而指数级增加，我们通过神经网络架构搜索技术，搜索最优的连接组合，使电商侧模型学习到更加有效的特征聚合模式，进而整合不同域空间信息，提升预估结果。

## 联合训练模型
我们提出联合训练方法，EFLS训练阶段除双方求交数据（remote）外，引入自定义数据（local）进行训练，能够灵活地使用己方数据，提升模型泛化能力。因该部分功能同时能在leader/follower侧引入，为便于理解下文以leader侧引入local数据为例进行阐述。

# 使用方法

## 环境准备

按文档准备好相关镜像，以下代码以`$HOME/workspace`为工作路径为例
```
mkdir -p $HOME/workspace
```

### 拉取代码

执行以下命令拉取demo代码
```
cd $HOME/workspace
# 下载EFLS代码
cd Elastic-Federated-Learning-Solution/efls-algo
```

### 原始数据

下载[Criteo数据集](https://www.kaggle.com/mrkmakr/criteo-dataset)

### 训练数据

使用以下命令进入数据求交docker容器
```
sudo docker run --net=host -it --rm --cpuset-cpus="0-63" -m 300G --name <YOUR_CONTAINER_NAME> -v $HOME/workspace:/workspace -w /workspace/Elastic-Federated-Learning-Solution/efls-algo <YOUR-ELFS-DATA-DOCKER-IMAGE> /bin/bash
```


### 数据构造

针对cotrain训练任务，需要对数据集进行切分生成local data 和remote data（生成数据有很多种方式，该部分为便于生成数据通过简单划分），remote部分进行数据求交，生成cotrain所需样本（local+remote）。以criteo数据为例：
```
split -l 500000 criteo.100w && mv xaa criteo_fl.50w && mv xab criteo_local.50w
```


此外，我们提供了两种训练数据的处理方法：`数据求交`和`local数据`

#### 数据求交

执行以下命令进行数据求交流程，完成后在当前目录下生成名为`data_join`的文件夹
```
./data/data_process.sh <YOUR_CRITEO_DATASET_PATH> data-join
```

#### local数据

执行以下命令进行数据求交流程，完成后在当前目录下生成名为`local_data`的文件夹
```
./data/data_process.sh <YOUR_CRITEO_DATASET_PATH> local
```

以上命令执行完毕后，可执行`exit`退出当前容器

## 模型训练

使用以下命令进入数据求交docker容器
```
sudo docker run --net=host -it --rm --cpuset-cpus="0-63" -m 300G --name <YOUR_CONTAINER_NAME> -v $HOME/workspace:/workspace -w /workspace/Elastic-Federated-Learning-Solution/efls-algo <YOUR-ELFS-TRAIN-DOCKER-IMAGE> /bin/bash
```

进入容器后可执行以下命令进行数据训练，日志会分别输出在当前文件夹下`leader.log`和`follower.log`文件
```
./bin/train_and_eval.sh <DATA_REMOTE_DIR> <DATA_LOCAL_DIR> data-join <MODEL_TYPE>
```
说明：

DATA_REMOTE_DIR: 求交remote部分训练数据目录。

DATA_LOCAL_DIR: local部分训练数据目录。

MODEL_TYPE：模型类型。如需要使用水平聚合模型则为`level`；如需使用层次聚合模型则为`hierarchical`；如需使用联合训练模型则为`cotrain`

如可以使用以下命令进行基于`remote数据和local数据`的联合模型训练
```
./bin/train_and_eval.sh ./data_join ./local_data data-join cotrain
```


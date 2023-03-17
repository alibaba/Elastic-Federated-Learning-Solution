# About Dataset
| Dataset|   
| :------: | 
| sample_train_aligned.tar.gz|
| sample_train_nonaligned.tar.gz | 
| sample_test |  

We release our data on tianchi platform, please download data by this [url](https://tianchi.aliyun.com/dataset/148347?spm=5176.12282013.0.0.1eed2f61qy5fB5)
## 1.Data Description
The dataset is built upon the click log of our e-commerce ad delivery business, in which both the online publisher and the advertising platform belong to Alibaba Group. Although the two parties belong to the same company, they still cannot share user behavior information to each other. Specifically, the online publisher is a mobile app that contains ad positions. As shown in Figure, the advertising platform bids for ad impressions through real-time bidding, and for each traffic request the predicted CVR score is a key factor in the bid price. If an ad from the advertising platform wins a bid, it will be displayed to the user. The user will arrive at another e-commerce mobile app that manages the ad landing page if he/she clicks on the ad, and may take further behaviors such as add-to-wishlist and purchase.

![picture](./pic.png)

The dataset is in format of $\{(x_{i} \rightarrow z_{i})\}|^{N}_{i=1}$，N is the total number of sample，$x_i$ represents feature vector of sample, which is usually a high dimensional sparse vector with multi-fields, such as user field,item field. Z indicating whether conversion event occurs.

## 2.Data Construction
We built the benchmark dataset based on the above collected data. Specifically, we collect 1-month consecutive user click events of the delivery business, and each sample in the dataset is corresponding to a unique click event.We split it to training set and test set based on click timestamp, where the last week’s samples are selected for test set.
### 2.1 Data collection
Each sample in the dataset is corresponding to a unique click event. Generally, the dataset is composed of features from **label party** & **non-label party**, and conversion labels from **label party**. The **label party** is composed of sections as belows:

- Sample ID：The unique identity of a record. It is the primary key of the sample skeleton file.

- Foreign key：Which is foreign key of sample, references the field with the same name.

- Conversion label：The conversion label of a sample is set to 1 if the user purchases the item described by the clicked ad, where the attribution window is set to 24 hours. The attribution approach is last-touch attribution, which means that if a user clicks on the ad multiple times and finally purchases the item, we regard that this conversion event is attributed by the last click event

The **non-label party** is composed of sections as belows:

- Sample ID：The unique identity of a record. It is the primary key of the sample skeleton file.

- Context：We record context information for each sample, such as the timestamps of click event and which type of the business.

- Foreign key：which is foreign key of sample, references the field with the same name.


### 2.2 Description of features
In summary, there are 16 features owned by label party and 7 features owned by non-label party. For the considerations of fair comparison and removing personal identifiable information, in our dataset we release the processed features rather than original values. Specifically, for discrete features we map the original values to IDs. For each continuous feature, we perform equi-frequency discretization to transform the original values to bin IDs.


<table>
	<tr>
		<td>Feature Field</td>
		<td>Feature ID</td>
		<td>Label Party or Non-label Party Field</td>
		<td>Description</td>
	</tr>
	<tr>
		<td rowspan="10">Item field</td>
		<td>l_i_fea_1</td>
		<td>Label</td>
		<td rowspan="3">Item profile</td>
	</tr>
	<tr>
		<td>l_i_fea_2</td>
		<td>Label</td>
	</tr>
	<tr>
		<td>l_i_fea_3</td>
		<td>Label</td>
	</tr>
	<tr>
		<td>l_i_fea_4</td>
		<td>Label</td>
		<td rowspan="3">Shop profile</td>
	</tr>
	<tr>
		<td>l_i_fea_5</td>
		<td>Label</td>
	</tr>
	<tr>
		<td>l_i_fea_6</td>
		<td>Label</td>
	</tr>
	<tr>
		<td>l_i_fea_7</td>
		<td>Label</td>
		<td rowspan="4">The popularity of Item</td>
	</tr>
	<tr>
		<td>l_i_fea_8</td>
		<td>Label</td>
	</tr>
	<tr>
		<td>l_i_fea_9</td>
		<td>Label</td>
	</tr>
	<tr>
		<td>l_i_fea_10</td>
		<td>Label</td>
	</tr>
	<tr>
		<td rowspan="10">User field</td>
		<td>l_u_fea_1</td>
		<td>Label/Non-label</td>
		<td rowspan="4">User profile</td>
	</tr>
	<tr>
		<td>l_u_fea_2</td>
		<td>Label</td>
	</tr>
	<tr>
		<td>l_u_fea_3</td>
		<td>Label</td>
	</tr>
	<tr>
		<td>l_u_fea_4</td>
		<td>Label</td>
	</tr>
	<tr>
		<td>l_u_fea_5</td>
		<td>Label</td>
		<td rowspan="2">User behavior features</td>
	</tr>
	<tr>
		<td>l_u_fea_6</td>
		<td>Label</td>
	</tr>
	<tr>
		<td>f_u_fea_1</td>
		<td>Non-label</td>
		<td rowspan="4">User browsing interests</td>
	</tr>
	<tr>
		<td>f_u_fea_2</td>
		<td>Non-label</td>
	</tr>
	<tr>
		<td>f_uc_fea_1</td>
		<td>Non-label</td>
	</tr>
	<tr>
		<td>f_uc_fea_2</td>
		<td>Non-label</td>
	</tr>
	<tr>
		<td rowspan="2">Context</td>
		<td>l_c_fea</td>
		<td>Non-label</td>
		<td rowspan="3">Context features</td>
	</tr>
	<tr>
		<td>f_c</td>
		<td>Non-label</td>
	</tr>

</table>



### 2.3 Sample join
In order to facilitate the use, we have completed sample join process, you can use it directly for training and testing directly. For aligned training set and test set, you have all the features from label party and non-label party. For unaligned training set, you only have the features of label party. 

## 3.Citation
To acknowledge use of the dataset in publications, please cite the following paper:

> ***.

## 4.License
The dataset is distributed under the [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/?spm=5176.12282016.0.0.313e492c7xmVCT) license.

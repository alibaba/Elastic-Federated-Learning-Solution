import React, { useState, useRef, useEffect } from 'react';
import { Button, message, Input, Drawer, Table, Badge, Card } from 'antd';
import { history } from 'umi';
import { useRequest } from 'ahooks';
import Back from '@/components/BackHistory';
import EditForm from './components/EditForm';
import styles from './styles.less';
import { createTask, updateTask, getTaskIntraInfo, } from './service';
import { Version } from './data';

interface AddTrainTaskProps {
  location: {
    pathname: string,
    query: {
      id: string,
    },
  };
};

const AddTrainTask: React.FC<AddTrainTaskProps> = (props) => {
  const { location: { pathname = '', query: { id } } } = props;
  const [versionInfo, setVersionInfo] = useState<Version | any>({});
  let mode = 'add';
  if (!!pathname && pathname.indexOf('/task/train/edit') >= 0) {
    mode = 'edit';
  };
  const title = mode == 'add' ? '创建训练任务' : '编辑训练任务';
  const editTask = mode == 'add' ? createTask : updateTask;

  const { loading, run: edit_task } = useRequest(editTask, {
    manual: true,
    onSuccess: (result: any, params) => {
      const { rsp_code } = result;
      if (rsp_code === 0) {
        message.success('操作成功!', 1, () => history.goBack());
      } else {
        message.error('操作失败');
      };
    },
  });

  const { loading: getTaskIntraInfoLoading, run: get_task_intra_info } = useRequest(getTaskIntraInfo, {
    manual: true,
    onSuccess: (result: any, params) => {
      const { data, rsp_code } = result;
      if (rsp_code == 0 && Object.keys(data).length > 0) {
        setVersionInfo(data);
      };
    },
  });

  useEffect(() => {
    if (id) { get_task_intra_info(id); };
  }, []);


  const formSubmit = (params: Version) => {
    const replenishData = {
      ...params,
      config: JSON.parse(params.config || "{}"),
      meta: JSON.parse(params.meta || "{}"),
      id
    };
    if (mode !== 'edit') {
      replenishData["task_root"] = false;
      replenishData["type"] = 1;
      replenishData["project_id"] = versionInfo?.project_id;
    };
    // mode !== 'edit' && (replenishData["task_root"] = false);
    edit_task({ ...replenishData });
  };

  const onCancel = () => {
    history.goBack();
  };


  return (
    <>
      <h2 className={styles.title_before}>{title}</h2>
      <EditForm formSubmit={formSubmit} onCancel={onCancel} versionInfo={versionInfo} mode={mode} loading={loading} />
    </>
  );
};

export default AddTrainTask;

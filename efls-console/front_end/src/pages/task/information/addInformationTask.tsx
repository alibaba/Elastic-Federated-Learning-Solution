import React, { useState, useRef, useEffect, useContext } from 'react';
import { Button, message, Input, Drawer, Table, Badge, Card } from 'antd';
import { history } from 'umi';
import { useRequest } from 'ahooks';
import Back from '@/components/BackHistory';
import EditForm from './components/EditForm';
import styles from './styles.less';
import { createInformationTask, updateInformationTask, getInformationTaskIntraInfo, } from './service';



interface AddInformationTaskProps {
  location: {
    pathname: string,
    query: {
      id: string,
    },
  };
};

const AddInformationTask: React.FC<AddInformationTaskProps> = (props) => {
  const { location: { pathname = '', query: { id } } } = props;
  const [versionInfo, setVersionInfo] = useState<any>({});
  let mode = 'add';
  if (!!pathname && pathname.indexOf('/task/sample/edit') >= 0) {
    mode = 'edit';
  };
  const title = mode == 'add' ? '创建数据任务' : '编辑数据任务';
  const editTask = mode == 'add' ? createInformationTask : updateInformationTask;

  const { loading, run: editInformationTask } = useRequest(editTask, {
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

  const { loading: getInformationTaskIntraInfoLoading, run: informationTaskIntraInfo } = useRequest(getInformationTaskIntraInfo, {
    manual: true,
    onSuccess: (result: any, params) => {
      const { data, rsp_code } = result;
      if (rsp_code == 0 && Object.keys(data).length > 0) {
        setVersionInfo(data);
      };
    }
  });

  useEffect(() => {
    if (id) { informationTaskIntraInfo(id); };
  }, []);

  const formSubmit = (params: any) => {
    const replenishData = {
      ...params,
      config: JSON.parse(params.config || "{}"),
      meta: JSON.parse(params.meta || "{}"),
      id,
    };
    if (mode !== 'edit') {
      replenishData["task_root"] = false;
      replenishData["type"] = 0;
      replenishData["project_id"] = versionInfo?.project_id;
    };
    // mode !== 'edit' && (replenishData["task_root"] = false);
    editInformationTask({ ...replenishData });
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

export default AddInformationTask;

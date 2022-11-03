import React, { useState, useRef, useContext } from 'react';
import { Button, message, Input, Drawer, Table, Badge, Card, Collapse } from 'antd';
import { PlusOutlined, } from '@ant-design/icons';
import { Access, history, useAccess, useModel, useRequest } from 'umi';
import type { ProColumns, ActionType } from '@ant-design/pro-table';
import ProTable from '@ant-design/pro-table';
import { TrainTaskTableColumns, TrainVersionTableColumns, } from './utils';
import { getTaskList, createTaskInter, instanceTaskRun, deleteTask } from './service';
import DrawerResources from './components/DrawerResources';
import styles from './styles.less';
import ProjectContext from "@/utils/ProjectContext";
import { TrainTaskTableList, Version } from './data';
import MainDiv from '@/components/MainDiv';
import DrawerTask from '@/pages/projects/components/DrawerTask';
interface TrainProps {
  location: {
    query: {
      projectId: string
    }
  }
};

const Train: React.FC<TrainProps> = (props) => {
  const { location: { query: { projectId } } } = props;
  const actionRef = useRef<ActionType>();
  const { expandedRowKeys: { train }, updateExpandedRowKeys, } = useModel('useExpandedRowKeys');
  const [visible, setVisible] = useState(false);
  const [versionInfo, setVersionInfo] = useState({});
  const [taskVisible, setTaskVisible] = useState(false);
  const { projectConfig } = useContext(ProjectContext);
  const access = useAccess();
  const renderTaskList = async () => {
    const { data: { task_list = [] }, rsp_code } = await getTaskList({ type: 1,project_id:projectId });
    let dataSource: TrainTaskTableList | any;
    if (rsp_code == 0 && task_list.length > 0) {
      dataSource = task_list.reduce((acc: any, obj: any) => {
        var key = `${obj.name}_${obj.project_id}`;
        if (!acc[key]) {
          acc[key] = {
            ...obj,
            version: []
          };
        };
        obj.version && acc[key]['version'].push({ ...obj });
        return acc;
      }, {});
      dataSource = Object.values(dataSource);
    };
    return {
      data: dataSource,
      total: dataSource.length,
      status: rsp_code == 0
    };
  };

  const { loading, run: taskDelete } = useRequest(deleteTask, {
    manual: true,
    onSuccess: (data: any, params) => {
      const { result } = data;
      if (result) {
        message.success('删除成功!', 1, () => refreshTable());
      } else {
        message.error('删除失败');
      }
    },
  });

  const expandedRowRender = (versionData: Version[] = []) => {
    const columns = TrainVersionTableColumns(pairTaskInter, versionStart, showDrawer,projectConfig.id, access, taskDelete);
    return <Table columns={columns} scroll={{ x: 1000 }} rowKey="id" dataSource={versionData} pagination={false} />;
  };

  const onCreate = () => {
    history.push('/task/train/add');
  };
  const refreshTable = () => {
    actionRef.current?.reload();
  }
  const pairTaskInter = (id: string) => {
    createTaskInter(id).then((res: any) => {
      const { rsp_code } = res;
      if (rsp_code === 0) {
        message.success('请求成功', 1, () => refreshTable());
      } else {
        message.error('请求失败')
      };
    })
  };

  const versionStart = (id: string) => {
    instanceTaskRun(id).then((res: any) => {
      const { rsp_code, message: info } = res;
      if (rsp_code === 0) {
        message.success('运行成功', 1, () => refreshTable());
      } else {
        message.error('运行失败', 1, () => refreshTable());
      }
    }).catch(err => message.error('运行失败', 1, () => refreshTable()));
  };

  const handleVisible = () => {
    setVisible(!visible)
  };
  const handleTaskVisible = (refresh?: boolean) => {
    setTaskVisible(!taskVisible);
    if (refresh) {
      refreshTable();
    }
  };

  const showDrawer = (versionData: Version) => {
    setVersionInfo(versionData);
    handleVisible();
  };

  const expandItem = (key: string) => {
    let newRowKeys = [...train];
    if (newRowKeys.includes(key)) {
      newRowKeys = newRowKeys.filter(r => r !== key);
    } else {
      newRowKeys.push(key);
    };
    updateExpandedRowKeys('train', newRowKeys);
  };

  return (
    <>
      <h2>训练任务</h2>
      <ProTable
        actionRef={actionRef}
        columns={TrainTaskTableColumns}
        request={async () => await renderTaskList()}
        rowKey="id"
        search={false}
        expandable={{
          rowExpandable: item => !!item['version'] && item['version'].length > 0,
          expandedRowRender: item => expandedRowRender(item?.version),
          expandedRowKeys: train,
          onExpand: (expanded, record) => expandItem(record.id),
        }}
        onRow={record => {
          return {
            onClick: event => expandItem(record.id),
          };
        }}
        toolBarRender={() => [
          <Access accessible={access.canAddTask} >
            <Button key="button" icon={<PlusOutlined />} onClick={() => { handleTaskVisible() }} type="primary">
              新建
            </Button>
          </Access>,
        ]}
        scroll={{ x: '100%' }}
      />
      <DrawerResources visible={visible} onClose={handleVisible} versionInfo={versionInfo} />
      <DrawerTask visible={taskVisible} onClose={handleTaskVisible} projectInfo={projectConfig} taskType={1} />
    </>
  );
};

export default Train;

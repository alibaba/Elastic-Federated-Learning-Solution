import React, { useState, useRef, useContext } from 'react';
import { Button, message, Input, Drawer, Table, Badge, Card } from 'antd';
import { PlusOutlined, } from '@ant-design/icons';
import { history, useModel } from 'umi';
import type { ProColumns, ActionType } from '@ant-design/pro-table';
import ProTable from '@ant-design/pro-table';
import ProjectContext from "@/utils/ProjectContext";
import { InformationTaskTableColumns, InformationVersionTableColumns, } from './utils';
import { getInformationTaskList, createInformationTaskInter, instanceInformationTaskRun } from './service';
import DrawerResources from '../train/components/DrawerResources';
import styles from './styles.less';
import { SampleTaskTableList, Version } from './data';
import DrawerTask from '@/pages/projects/components/DrawerTask';
interface InformationProps {
  location: {
    query: {
      projectId: string
    }
  }
};
const Information: React.FC<InformationProps> = (props) => {
  const actionRef = useRef<ActionType>();
  const { location: { query: { projectId } } } = props;
  const { expandedRowKeys: { sample }, updateExpandedRowKeys, } = useModel('useExpandedRowKeys');
  const [visible, setVisible] = useState(false);
  const [versionInfo, setVersionInfo] = useState({});
  const { projectConfig } = useContext(ProjectContext);
  const [taskVisible, setTaskVisible] = useState(false)
  const renderTaskList = async () => {
    const { data: { task_list = [] }, rsp_code } = await getInformationTaskList({ type: 0,project_id:projectId });
    let dataSource: SampleTaskTableList | any;
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


  const expandedRowRender = (versionData: Version[] = []) => {
    const columns = InformationVersionTableColumns(pairTaskInter, instanceRun, showDrawer, projectConfig.id);
    return <Table columns={columns} dataSource={versionData} pagination={false} rowKey="id" scroll={{ x: 1000 }} />;
  };

  const onCreate = () => {
    history.push('/app/task/sample/add');
  };

  const refreshTable = () => {
    actionRef.current?.reload();
  }
  //配对
  const pairTaskInter = (id: string) => {
    createInformationTaskInter(id).then((res: any) => {
      const { rsp_code } = res;
      if (rsp_code === 0) {
        message.success('请求成功', 1, () => refreshTable());
      } else {
        message.error('请求失败')
      };
    })
  };

  //运行
  const instanceRun = (id: string) => {
    instanceInformationTaskRun(id).then((res: any) => {
      const { rsp_code } = res;
      if (rsp_code === 0) {
        message.success('运行成功', 1, () => refreshTable());
      } else {
        message.error('运行失败');
      };
    })
  };

  const handleVisible = () => {
    setVisible(!visible);
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
    let newRowKeys = [...sample];
    if (newRowKeys.includes(key)) {
      newRowKeys = newRowKeys.filter(r => r !== key);
    } else {
      newRowKeys.push(key);
    };
    updateExpandedRowKeys('sample', newRowKeys);
  };


  return (
    <>
      <h2>数据任务</h2>
      <ProTable
        actionRef={actionRef}
        columns={InformationTaskTableColumns}
        request={async () => await renderTaskList()}
        rowKey="id"
        search={false}
        expandable={{
          rowExpandable: item => !!item['version'] && item['version'].length > 0,
          expandedRowRender: item => expandedRowRender(item?.version),
          expandedRowKeys: sample,
          onExpand: (expanded, record) => expandItem(record.id),
        }}
        onRow={record => {
          return {
            onClick: event => expandItem(record.id),
          };
        }}
        toolBarRender={() => [
          <Button key="button" icon={<PlusOutlined />} onClick={() => { handleTaskVisible() }} type="primary">
            新建
              </Button>,
        ]}
      />
      <DrawerResources visible={visible} onClose={handleVisible} versionInfo={versionInfo} />
      <DrawerTask visible={taskVisible} onClose={handleTaskVisible} projectInfo={projectConfig} taskType={0} />
    </>
  );
};

export default Information;

import React, { useState, useRef, useEffect, useContext } from 'react';
import { Button, message, Input, Drawer, Table, Badge, Divider, Card, Popconfirm } from 'antd';
import { PageHeaderWrapper } from '@ant-design/pro-layout';
import { SlidersOutlined, EyeOutlined, EyeInvisibleOutlined, ReloadOutlined, PlaySquareOutlined } from '@ant-design/icons';
import ProDescriptions from '@ant-design/pro-descriptions';
import type { ProColumns, ActionType } from '@ant-design/pro-table';
import ProTable from '@ant-design/pro-table';
import { Access, history, useAccess } from 'umi';
import { useRequest } from 'ahooks';
import ProjectContext from "@/utils/ProjectContext";
import styles from './styles.less';
import { getTaskIntraInfo, getTaskInterInfo, getTaskInstanceList, taskInstanceStatus, instanceTaskRun, instanceTaskUpdate, instanceTaskDelete } from './service';
import { TrainInstanceTableColumns } from './utils';


interface versionDetailsProps {
  location: {
    pathname: string,
    query: {
      id: string,
    },
  };
};

const versionDetails: React.FC<versionDetailsProps> = (props) => {
  const { location: { query: { id } } } = props;
  const actionRef = useRef<ActionType>();
  const { projectConfig } = useContext(ProjectContext);
  const [configVisible, setConfigVisible] = useState(false);
  const [versionInfo, setVersionInfo] = useState<any>({});
  const [versionInterInfo, setVersionInterInfo] = useState<any>();
  const btn = !configVisible ? <><EyeOutlined /> 查看对方配置</> : <><EyeInvisibleOutlined /> 隐藏对方配置</>;
  const access = useAccess();

  const { loading, run: get_task_intra_info } = useRequest(getTaskIntraInfo, {
    manual: true,
    onSuccess: (result: any, params) => {
      const { data, rsp_code } = result;
      if (rsp_code == 0 && Object.keys(data).length > 0) {
        setVersionInfo(data);
      };
    }
  });

  const { loading: intertLoading, run: get_task_inter_info } = useRequest(getTaskInterInfo, {
    manual: true,
    onSuccess: (result: any, params) => {
      const { data, rsp_code } = result;
      if (rsp_code == 0 && Object.keys(data).length > 0) {
        setVersionInterInfo(JSON.stringify(data?.peer_task_rsp));
      };
    }
  });

  const { loading: deleteLoading, run: instanceDelete } = useRequest(instanceTaskDelete, {
    manual: true,
    onSuccess: (result: any, params) => {
      const { rsp_code } = result;
      if (rsp_code == 0 ) {
        message.success('删除成功!', 1, () => refreshTable());
      } else {
        message.error('删除失败');
      }
    }
  });

  useEffect(() => {
    if (configVisible) {
      if (!versionInterInfo) {
        get_task_inter_info(versionInfo.task_inter_id)
      };
    };
  }, [configVisible])

  useEffect(() => {
    if (id) {
      get_task_intra_info(id)
    }
  }, []);

  useEffect(() => {
    if (versionInfo.task_inter_id) {
      refreshTable();
    };
  }, [versionInfo.task_inter_id]);

  const refreshTable = () => {
    actionRef.current?.reload();
  }

  const renderTaskInstanceList = async (params: any) => {
    const task_inter_id = versionInfo.task_inter_id;
    if (task_inter_id) {
      const { data: { task_instance_list = [], total }, rsp_code } = await getTaskInstanceList({ task_inter_id, ...params });
      return {
        data: task_instance_list,
        total: total,
        status: rsp_code == 0
      };
    }
  };

  const handleInstanceRun = (params: any) => {
    taskInstanceStatus(params).then((res: any) => {
      const { rsp_code, message: info } = res;
      if (rsp_code === 0) {
        message.success('操作成功', 1, () => refreshTable());
      } else {
        message.error(`操作失败${info ?? ''} `);
      };
    }).catch(err => {
      message.error('操作失败');
    });
  };

  const handleInstanceUpdate = (id: any) => {
    instanceTaskUpdate({ id, "need_sync": true }).then((res: any) => {
      const { rsp_code, message: info } = res;
      if (rsp_code === 0) {
        message.success('更新成功', 1, () => refreshTable());
      } else {
        message.error(`更新失败${info ?? ''} `);
      };
    }).catch(err => {
      message.error('操作失败');
    });
  };

  const versionStart = () => {
    instanceTaskRun(versionInfo.task_inter_id).then((res: any) => {
      const { rsp_code, message: info } = res;
      if (rsp_code === 0) {
        message.success('运行成功', 1, () => refreshTable());
      } else {
        message.error('运行失败', 1, () => refreshTable());
      }
    }).catch(err => message.error('运行失败', 1, () => refreshTable()));
  };

  const checkJson = (config: any) => {
    let tmpConfig;
    try {
      if (typeof config == 'object') {
        tmpConfig = JSON.stringify(config);
      } else {
        tmpConfig = config;
      }
    } catch (e) {
      tmpConfig = "";
      console.error('parse json', e);
    }
    return tmpConfig;
  };

  const columns = TrainInstanceTableColumns(handleInstanceRun, handleInstanceUpdate, projectConfig?.id, instanceDelete);
  const runBtn = versionInfo.status === 1 || versionInfo.status === 2;

  return (
    <>
      {
        Object.keys(versionInfo).length > 0 &&
        <ProDescriptions column={2} title={<h3 className={styles.h2_before}>版本详情</h3>}>
          <ProDescriptions.Item label="关联项目">
            {versionInfo.project_name}
          </ProDescriptions.Item>
          {/* <ProDescriptions.Item label="ID">
            {versionInfo.id}
          </ProDescriptions.Item> */}
          <ProDescriptions.Item label="训练任务名称">
            {versionInfo.name}
          </ProDescriptions.Item>
          <ProDescriptions.Item label="创建人">
            {versionInfo.owner_name}
          </ProDescriptions.Item>
          <ProDescriptions.Item label="token" span={2}>
            {versionInfo.token}
          </ProDescriptions.Item>
          <ProDescriptions.Item label="comment" span={2}>
            {versionInfo.comment ?? '-'}
          </ProDescriptions.Item>
          <ProDescriptions.Item label="内部配置" valueType="jsonCode" contentStyle={{ overflow: 'auto', overflowY: 'scroll', maxHeight: 406 }}>
            {checkJson(versionInfo.config)}
          </ProDescriptions.Item>
          <ProDescriptions.Item label="对外配置" valueType="jsonCode" contentStyle={{ overflow: 'auto', overflowY: 'scroll', maxHeight: 406 }}>
            {checkJson(versionInfo.meta)}
          </ProDescriptions.Item>
          <ProDescriptions.Item label="文本" valueType="option">
            {runBtn &&
              <Access accessible={access.canRun} >
                <Popconfirm title="确认运行?" onConfirm={versionStart} okText="确认" cancelText="取消">
                  <Button style={{ margin: 0, padding: "0px 6px", height: "28px" }}><PlaySquareOutlined />运行实例</Button>
                </Popconfirm>
              </Access>
            }
            <Button style={{ margin: 0, padding: "0px 6px", height: "28px" }} onClick={() => setConfigVisible(!configVisible)}>{btn}</Button>
          </ProDescriptions.Item>
        </ProDescriptions>
      }
      <div>
        {configVisible && <>
          <Divider orientation="left">对方配置信息</Divider>
          <ProDescriptions>
            <ProDescriptions.Item label="配置信息" valueType="jsonCode" contentStyle={{ overflow: 'auto', overflowY: 'scroll', maxHeight: 406 }}>
              {checkJson(versionInterInfo)}
            </ProDescriptions.Item>
          </ProDescriptions>
        </>}
      </div>

      <Divider orientation="left"  >instance列表</Divider>
      <ProTable
        actionRef={actionRef}
        columns={columns}
        request={async ({ current: page_num, pageSize: page_size }) => await renderTaskInstanceList({ page_num, page_size })}
        rowKey="id"
        search={false}
        manualRequest={false}
        pagination={{
          pageSize: 10,
        }}
      />
    </>
  );
};

export default versionDetails;
import React, { useState, useRef, useEffect } from 'react';
import { Button, message, Input, Drawer, Table, Badge, Divider, Card, Modal } from 'antd';
import { history } from 'umi';
import { useRequest } from 'ahooks';
import ProDescriptions from '@ant-design/pro-descriptions';
import type { ProDescriptionsActionType } from '@ant-design/pro-descriptions';
import styles from '../styles.less';
import { getInformationTaskInstanceDetails } from '../service';

interface versionDetailsProps {
  location: {
    pathname: string,
    query: {
      id: string,
    },
  };
};

const statusEnum = {
  0: { text: 'DRAFT', status: 'Default' },
  1: { text: 'READY', status: 'processing' },
  2: { text: 'ARCHIVE', status: 'error' },
  3: { text: 'RUNNING', status: 'processing' },
  4: { text: 'FAILED', status: 'error' },
  5: { text: 'TERMINATED', status: 'error' },
};
const versionDetails: React.FC<versionDetailsProps> = (props) => {
  const { location: { query: { id } } } = props;
  const actionRef = useRef<ProDescriptionsActionType>();
  const [instanceInfo, setInstanceInfo] = useState();

  const formatGmt = (data: any) => {
    for (let key in data) {
      if (key.indexOf("gmt_") >= 0) {
        data[key] = (data[key] * 1000);
      } else if (typeof data[key] == "object") {
        formatGmt(data[key]);
      };
    };
    return data;
  };

  const getInformationTaskInstanceInfo = async () => {
    const { data, rsp_code } = await getInformationTaskInstanceDetails(id);
    setInstanceInfo(data);
    const dataSource = formatGmt(data);
    return {
      success: rsp_code === 0,
      data: dataSource,
    };
  };

  const checkLog = (log: string) => {
    let logLink;
    try {
      log = JSON.parse(log);
      logLink = log["job_log_link"];
    } catch (error) { console.error('log转换失败') }
    return <Button type='link' style={btnStyle} href={logLink} target="_blank" disabled={!logLink}>查看</Button>
  };

  const btnStyle = { margin: 0, padding: 0, height: 20 };

  return (
    <>
      <ProDescriptions
        actionRef={actionRef}
        title={<h3 className={styles.title_before}>实例详情</h3>}
        request={async () => {
          const data = await getInformationTaskInstanceInfo();
          return data;
        }}
        column={4}
      >
        <ProDescriptions.Item dataIndex="id" label="instanceId" span={2} />
        {/* <ProDescriptions.Item dataIndex="task_inter_id" label="task_inter_id" span={2} /> */}
        <ProDescriptions.Item dataIndex="task_intra_name" label="task_intra_name" span={2} />
        {/* <ProDescriptions.Item dataIndex="task_peer_id" label="task_peer_id" span={2} /> */}
        <ProDescriptions.Item dataIndex="status" label="状态" valueType="select"
          valueEnum={statusEnum} span={2} />
        <ProDescriptions.Item dataIndex="gmt_create" label="创建时间" valueType="dateTime" span={2} />
        <ProDescriptions.Item dataIndex="gmt_error" label="异常时间" valueType="dateTime" span={2} />
        <ProDescriptions.Item dataIndex="gmt_modified" label="修改时间" valueType="dateTime" span={2} />
        <ProDescriptions.Item dataIndex="gmt_start" label="启动时间" valueType="dateTime" span={2} />
        <ProDescriptions.Item label="message" span={4}>
          {checkLog(instanceInfo?.message)}
        </ProDescriptions.Item>
        <ProDescriptions.Item label="error" span={4} >
          {checkLog(instanceInfo?.error)}
        </ProDescriptions.Item>
        <ProDescriptions.Item span={4}>
          <Divider orientation="right" plain><h3>instance对方信息</h3></Divider>
        </ProDescriptions.Item>
        <ProDescriptions.Item dataIndex={["task_instance_peer", "id"]} label="instanceId" span={2} />
        {/* <ProDescriptions.Item dataIndex={["task_instance_peer", "task_inter_id"]} label="task_inter_id" span={2} /> */}
        <ProDescriptions.Item dataIndex={["task_instance_peer", "task_intra_name"]} label="task_intra_name" span={2} />
        {/* <ProDescriptions.Item dataIndex={["task_instance_peer", "task_peer_id"]} label="task_peer_id" span={2} /> */}
        <ProDescriptions.Item dataIndex={["task_instance_peer", "status"]} label="状态" valueType="select"
          valueEnum={statusEnum} span={2} />
        <ProDescriptions.Item dataIndex={["task_instance_peer", "gmt_create"]} label="创建时间" valueType="dateTime" span={2} />
        <ProDescriptions.Item dataIndex={["task_instance_peer", "gmt_error"]} label="异常时间" valueType="dateTime" span={2} />
        <ProDescriptions.Item dataIndex={["task_instance_peer", "gmt_modified"]} label="修改时间" valueType="dateTime" span={2} />
        <ProDescriptions.Item dataIndex={["task_instance_peer", "gmt_start"]} label="启动时间" valueType="dateTime" span={2} />
        <ProDescriptions.Item label="message" span={4}>
          {checkLog(instanceInfo?.task_instance_peer?.message)}
        </ProDescriptions.Item>
        <ProDescriptions.Item label="error" span={4} >
          {checkLog(instanceInfo?.task_instance_peer?.error)}
        </ProDescriptions.Item>
        <ProDescriptions.Item label="文本" valueType="option">
          <a onClick={() => { actionRef.current?.reload(); }}>刷新</a>
        </ProDescriptions.Item>
      </ProDescriptions>
    </>
  );
};

export default versionDetails;
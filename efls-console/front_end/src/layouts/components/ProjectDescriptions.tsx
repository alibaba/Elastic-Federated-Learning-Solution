import React, { FC, useContext, useState } from 'react';
import { Card, Tooltip, Button } from 'antd';
import { useRequest } from 'ahooks';
import { history } from 'umi';
import ProDescriptions from '@ant-design/pro-descriptions';
import { FundProjectionScreenOutlined, ApiOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import ProjectContext from "@/utils/ProjectContext";
import { getProjectConnect } from '@/pages/projects/service';
import styles from './style.less';
import { RootObject } from '../data';

interface ProjectDescriptionsProps {
};

const ProjectDescriptions: FC<ProjectDescriptionsProps> = props => {
  const { projectConfig } = useContext(ProjectContext);
  const [projectStatus, setProjectStatus] = useState(0);

  const { loading, run: get_project_connect } = useRequest(getProjectConnect, {
    manual: true,
    onSuccess: (result, params) => {
      const { rsp_code, data: { project_id } } = result;
      if (rsp_code === 0 && project_id) {
        setProjectStatus(1);
      } else {
        setProjectStatus(2);
      };
    },
  });

  const inspectProjectStatus = () => {
    get_project_connect(projectConfig?.id);
  };


  const btnStyle = {
    color: '#4e5969',
    width: 22,
    height: 22
  };

  if (!!projectConfig && Object.keys(projectConfig).length > 0) {
    return (
      <Card style={{ marginBottom: 10 }} className={styles.descriptions} >
        <ProDescriptions column={10}>
          <ProDescriptions.Item  span={1}>
            <a 
              style={{width:'3em'}}
              onClick={() => {
              history.goBack();
            }}><ArrowLeftOutlined  style={{fontSize:'20px'}}/> </a>
          </ProDescriptions.Item>
          <ProDescriptions.Item label="项目名称" span={2}>
            {projectConfig.name}
          </ProDescriptions.Item>
          <ProDescriptions.Item
            label="项目状态"
            span={2}
            valueEnum={{
              0: { text: 'DRAFT', status: 'Default' },
              1: {
                text: 'READY',
                status: 'Success',
              },
              2: {
                text: 'ARCHIVE',
                status: 'Error',
              },
            }}
          >
            {projectConfig.status}
          </ProDescriptions.Item>
          <ProDescriptions.Item
            span={2}
            label="项目连接状态"
            valueEnum={{
              0: { text: 'DRAFT', status: 'Default' },
              1: {
                text: '成功',
                status: 'Success',
              },
              2: {
                text: '失败',
                status: 'Error',
              },
            }}
          >
            {projectStatus}
          </ProDescriptions.Item>
          <ProDescriptions.Item
            span={2}
            label="操作项"
          >
            <Tooltip title="检查连接">
              <Button type="text" icon={<ApiOutlined />} style={{ ...btnStyle }} onClick={inspectProjectStatus}
              />
            </Tooltip>
          </ProDescriptions.Item>
        </ProDescriptions>
      </Card>
    );
  };
  return null;
};

export default ProjectDescriptions;

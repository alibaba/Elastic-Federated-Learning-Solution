import React, { useState, useRef, useEffect } from 'react';
import { useRequest } from 'ahooks';
import { Drawer, Form, Button, Col, Row, Input, Select, DatePicker, Divider, message } from 'antd';
import ProDescriptions from '@ant-design/pro-descriptions';
import FormDetails from './FormDetails';
import { getProjectDetails, updateProject } from '../service';


const { Option } = Select;

interface DrawerFormProps {
  visible: boolean;
  projectInfo: { id: string, name: string };
  onClose: () => void;
  refreshProject: () => void;
};

const DrawerForm: React.FC<DrawerFormProps> = (props) => {
  const { visible, onClose, projectInfo, refreshProject, } = props;
  const [form] = Form.useForm();
  const [config, setConfig] = useState<any>({})

  const { loading, run: get_project_details } = useRequest(getProjectDetails, {
    manual: true,
    onSuccess: (result, params) => {
      const { data, rsp_code } = result;
      if (rsp_code === 0 && Object.keys(data).length > 0) {
        setConfig(data);
      };
    },
  });

  const { loading: updateProjectLoading, run: update_project } = useRequest(updateProject, {
    manual: true,
    onSuccess: (result: any, params) => {
      const { rsp_code } = result;
      if (rsp_code === 0) {
        message.success('操作成功', 1, () => { onClose(); refreshProject() });
      } else {
        message.error('操作失败');
      };
    },
  });

  useEffect(() => {
    if (visible) {
      get_project_details(projectInfo.id);
    } else {
      form.resetFields();
    };
  }, [visible]);

  useEffect(() => {
    if (Object.keys(config).length > 0) {
      form.setFieldsValue({ ...config });
    };
  }, [config]);

  const formLayuot = {
    labelCol: {
      span: 4,
    },
    wrapperCol: {
      span: 18,
    }
  };

  return (
    <Drawer
      title={projectInfo.name}
      width={820}
      onClose={onClose}
      visible={visible}
      bodyStyle={{ paddingBottom: 80 }}
    >
      <Form layout="horizontal"
        {...formLayuot}
        form={form} onFinish={(values) => {
          update_project({
            ...values,
            config: JSON.parse(values.config ?? '{}'),
            id: projectInfo.id
          })
        }}>
        <FormDetails title="我方项目配置" submitLoading={updateProjectLoading} peerUrl={config.peer_url} />
      </Form>

      <Divider orientation="left" plain>对方项目配置</Divider>
      <div>
        <ProDescriptions column={2}>
          <ProDescriptions.Item span={2} label="配置项" valueType="jsonCode">
            {config.peer_config}
          </ProDescriptions.Item>
        </ProDescriptions>
      </div>
    </Drawer>
  );
};

export default DrawerForm;

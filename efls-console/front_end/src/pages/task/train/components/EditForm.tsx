import React, { useState, useEffect, useRef } from 'react';
import { Button, message, Input, Drawer, Table, Badge, Form, Radio } from 'antd';
import WSEditorFormItem from '@/components/Monaco/WSEditorFormItem';
import { Version } from '../data';
import {  trainConfigTips } from '@/pages/projects/components/configConst';
interface EditFormProps {
  formSubmit: (params: Version) => void;
  onCancel: () => void;
  versionInfo: Version;
  loading: boolean;
  mode: string;
}

const EditForm: React.FC<EditFormProps> = (props) => {
  const { formSubmit, onCancel, versionInfo, loading, mode } = props;
  const [form] = Form.useForm();
  const [seniorVisible, setSeniorvisible] = useState(false);
  const formLayuot = {
    labelCol: {
      span: 4,
    },
    wrapperCol: {
      span: 16,
    }
  };
  const buttonLayout = {
    wrapperCol: { offset: 2 },
  };

  useEffect(() => {
    if (!!versionInfo && Object.keys(versionInfo).length > 0) {
      const config = checkJson(versionInfo.config ?? '{}');
      const meta = checkJson(versionInfo.meta ?? '{}');
      form.setFieldsValue({
        ...versionInfo,
        config,
        meta,
      });
    };
  }, [versionInfo]);

  const jsonValidator = async (rule, value) => {
    try {
      JSON.parse(value);
    } catch (e) {
      throw new Error('配置项必须为标准json格式,不能为空');
    }
  }
  const checkJson = (config: any) => {
    let tmpConfig;
    try {
      if (typeof config !== 'object') {
        config = JSON.parse(config);
      };
      tmpConfig = JSON.stringify(config, null, 2);
    } catch (e) {
      tmpConfig = config;
      console.warn('json解析异常', e);
    }
    return tmpConfig;
  };

  return (
    <Form
      form={form}
      {...formLayuot}
      onFinish={(values: Version) => formSubmit({ ...values })}
    >

      {mode == "add" && <>
        <Form.Item name="name" label="训练任务名称">
          <Input disabled />
        </Form.Item>
        <Form.Item name="project_name" label="关联项目" >
          <Input disabled />
        </Form.Item>
        <Form.Item name="token" label="token">
          <Input disabled />
        </Form.Item>
      </>}


      {mode == "edit" && <>
        <Form.Item label="训练任务名称">
          {versionInfo.name}
        </Form.Item>
        <Form.Item label="关联项目" >
          {versionInfo.project_name}
        </Form.Item>
        <Form.Item label="version">
          {versionInfo.version}
        </Form.Item>
      </>
      }

      {
        mode == "edit" && versionInfo.task_root && <Form.Item
          name="token"
          label="token"
          rules={[{ required: true, message: 'token不能为空' },]}>
          <Input />
        </Form.Item>
      }

      <Form.Item name="comment" label="comment">
        <Input.TextArea />
      </Form.Item>

      <Form.Item
        name="config"
        label="内部配置"
        tooltip={{title:trainConfigTips,overlayStyle:{maxWidth:'600px'}}}
        rules={[
          {
            validator: jsonValidator
          }
        ]}
        style={{ marginBottom: 0 }}
      >
        <WSEditorFormItem fileName="" style={{ height: '400px' }} />
      </Form.Item>

      <Form.Item  {...{ wrapperCol: { offset: 3 } }}>
        <Button type="link" onClick={() => setSeniorvisible(!seniorVisible)}>{!seniorVisible ? '+' : '-'} 高级配置</Button>
      </Form.Item>

      <Form.Item
        name="meta"
        label="对外配置"
        rules={[
          {
            validator: jsonValidator
          }
        ]}
        style={{ display: seniorVisible ? "flex" : "none" }}
      >
        <WSEditorFormItem fileName="" style={{ height: '400px' }} showMessage={true} message="警告: 对外配置信息为对方可见!" />
      </Form.Item>

      <Form.Item {...buttonLayout}>
        <Button
          type="primary"
          style={{ marginLeft: '15px', marginRight: '10px' }}
          loading={loading}
          htmlType="submit"
        >
          提交
        </Button>
        <Button onClick={onCancel}>取消</Button>
      </Form.Item>
    </Form>

  );
};

export default EditForm;

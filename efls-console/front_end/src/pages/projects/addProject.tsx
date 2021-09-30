import React, { useState, useRef } from 'react';
import { useRequest } from 'ahooks';
import { history } from 'umi';
import { Button, Divider, Form, Input, message } from 'antd';
import styles from './styles.less';
import WSEditorFormItem from '@/components/Monaco/WSEditorFormItem';
import { createProject } from './service';
import { ProjectCreateParams } from './data';

const addProject: React.FC = () => {
  const [form] = Form.useForm()
  const formLayuot = {
    labelCol: {
      span: 3,
    },
    wrapperCol: {
      span: 8,
    }
  };

  const { loading, run } = useRequest(createProject, {
    manual: true,
    onSuccess: (result: any, params) => {
      const { rsp_code, message: messageInfo } = result;
      if (rsp_code === 0) {
        message.success('操作成功!', 1, () => history.push('/projects'));
      } else {
        message.error(`操作失败: ${messageInfo}`);
      };
    },
  });

  const submitProject = (values: ProjectCreateParams) => {
    run({ ...values, config: JSON.parse(values.config ?? '{}') });
  };
  const initial = {
    config: '{}'
  }
  return (
    <div className={styles.project_add}>
      <h2 style={{ marginBottom: 10 }}>创建项目</h2>
      <Form
        form={form}
        {...formLayuot}
        labelAlign="right"
        initialValues={initial}
        onFinish={(values: ProjectCreateParams) => submitProject(values)}
      >
        <div>
          <h4 className={styles.h4_before}>基础信息</h4>
          <Form.Item
            name="name"
            label="项目名称"
            rules={[
              { required: true, message: '项目名称不能为空' },
            ]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="comment"
            label="项目说明"
            rules={[
              { required: true, message: '项目说明不能为空' },
            ]}>
            <Input.TextArea />
          </Form.Item>
        </div>
        <Divider orientation="center"></Divider>
        <div>
          <h4 className={styles.h4_before}>合作伙伴信息</h4>
          <Form.Item name="peer_url" label="合作伙伴地址"
            rules={[
              { required: true, message: '合作伙伴地址不能为空' },
            ]}>
            <Input />
          </Form.Item>
          <Form.Item name="config" label="配置项"
            rules={[
              {
                validator: async (rule, value) => {
                  try {
                    JSON.parse(value);
                  } catch (e) {
                    throw new Error('配置项必须为标准json格式,不能为空');
                  }
                }
              }
            ]}
          >
            <WSEditorFormItem fileName="" style={{ height: '300px' }} />
          </Form.Item>
        </div>
        <Form.Item wrapperCol={{ offset: 3, span: 16 }}>
          <Button type="primary" htmlType="submit" loading={loading} style={{ marginRight: 10 }}>
            确认
          </Button>
          <Button onClick={() => history.goBack()}>
            取消
          </Button>
        </Form.Item>
      </Form>
    </div >
  );
};

export default addProject;

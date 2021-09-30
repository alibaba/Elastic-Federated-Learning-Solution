import React, { useState, useRef, useEffect } from 'react';
import { Drawer, Form, Button, Col, Row, Input, Select, DatePicker, Divider } from 'antd';
import WSEditorFormItem from '@/components/Monaco/WSEditorFormItem';

const { Option } = Select;

interface FormDetailsProps {
  title: string;
  submitLoading: boolean;
  peerUrl: string
};

const FormDetails: React.FC<FormDetailsProps> = (props) => {
  const { title, submitLoading, peerUrl } = props;
  return (
    <>
      <Divider orientation="left" plain>{title}</Divider>
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
      <Form.Item label="合作伙伴地址">
        {peerUrl}
      </Form.Item>
      <Form.Item
        name="config"
        label="配置项"
        style={{ marginBottom: 0 }}
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
      <Form.Item >
        <Button
          type="primary"
          style={{ marginRight: '10px' }}
          htmlType="submit"
          loading={submitLoading}
        >
          更新配置
        </Button>
      </Form.Item>
    </>
  );
};

export default FormDetails;

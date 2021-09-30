import React, { useState, useRef, useEffect } from 'react';
import { useRequest, } from 'ahooks';
import { Drawer, Form, Button, Col, Row, Input, Select, DatePicker, Divider, message, Radio, Upload } from 'antd';
import { getTaskName, createTask } from '../../task/train/service';
import WSEditorFormItem from '@/components/Monaco/WSEditorFormItem';
import { ProjectConfig, CreateTaskParams } from '../data';
import { trainConfigTips, trainDefault, sampleConfigTips, sampleDefault } from './configConst';
import styles from './style.less';
const { Option } = Select;
enum TaskTypeEnum {
  SAMPLE = 0,
  TRAIN = 1
}
interface DrawerTaskProps {
  visible: boolean;
  projectInfo?: ProjectConfig;
  taskType: TaskTypeEnum;
  onClose: (refresh?: boolean) => void;
};


const DrawerTask: React.FC<DrawerTaskProps> = (props) => {
  const { visible, onClose, projectInfo, taskType } = props;
  const [form] = Form.useForm();
  const [type, setType] = useState(0);

  const formLayuot = {
    labelCol: {
      span: 4,
    },
    wrapperCol: {
      span: 19,
    }
  };

  const { loading, run: create_task } = useRequest(createTask, {
    manual: true,
    onSuccess: (result, params) => {
      const { rsp_code } = result;
      if (rsp_code === 0) {
        message.success('创建成功', 1, () => onClose(true));
      } else {
        message.error('操作失败');
      };
    },
  });

  useEffect(() => {
    if (visible) {
      form.setFieldsValue({
        "project_id": projectInfo.id
      });
    } else {
      form.resetFields();
    };
  }, [visible]);

  const checkName = async (_, val) => {
    if (val) {
      const { rsp_code, data } = await getTaskName(val);
      if (rsp_code == 0 && !data.name_exist) {
        return Promise.resolve();
      } else {
        return Promise.reject('任务名称重复');
      };
    };
  };
  const initialValue = {
    type: taskType,
    config: taskType === TaskTypeEnum.SAMPLE ? sampleDefault : trainDefault,
    meta: '{}'
  }
  const jsonValidator = async (rule, value) => {
    try {
      JSON.parse(value);
    } catch (e) {
      throw new Error('配置项必须为标准json格式,不能为空');
    }
  }

  return (
    <Drawer
      title="创建任务"
      width={720}
      onClose={onClose}
      visible={visible}
      bodyStyle={{ paddingBottom: 80 }}
    >
      <Form
        form={form}
        initialValues={initialValue}
        {...formLayuot}
        onFinish={(values: CreateTaskParams) => {
          const params = {
            ...values,
            task_root: true,
            config: JSON.parse(values.config ?? "{}"),
            meta: JSON.parse(values.meta ?? "{}"),
          };
          create_task({ ...params });
        }}
      >
        <Form.Item
          name="project_id"
          label="关联项目ID"
          rules={[{ required: true, message: '关联项目ID不能为空' },]}>
          <Input disabled={true} />
        </Form.Item>
        <Form.Item
          name="name"
          label="任务名称"
          style={{ marginBottom: 20 }}
          hasFeedback
          rules={[
            { required: true, message: '任务名称不能为空' },
            {
              validator: checkName,
            },
          ]}>
          <Input />
        </Form.Item>

        <Form.Item
          name="type"
          label="任务类型"
          rules={[{ required: true, message: '请选择任务类型' },]}>
          <Radio.Group disabled={true}>
            <Radio value={0}>SAMPLE</Radio>
            <Radio value={1}>TRAIN</Radio>
          </Radio.Group>
        </Form.Item>
        <Form.Item name="comment" label="comment">
          <Input.TextArea />
        </Form.Item>
        <Form.Item
          name="config"
          label="内部配置"
          tooltip={{ title: taskType === TaskTypeEnum.SAMPLE ? sampleConfigTips : trainConfigTips, overlayClassName:styles.tooltip }}
          rules={[
            {
              validator: jsonValidator
            }
          ]}
          style={{ marginBottom: 0 }}
        >
          <WSEditorFormItem fileName="" style={{ height: '400px' }} />
        </Form.Item>
        <Form.Item
          name="meta"
          label="对外配置"
          rules={[
            {
              validator: jsonValidator
            }
          ]}
          style={{ marginBottom: 0 }}
        >
          <WSEditorFormItem fileName="" style={{ height: '400px' }} />
        </Form.Item>
        <Form.Item>
          <Button
            type="primary"
            style={{ marginLeft: '15px', marginRight: '10px' }}
            loading={loading}
            htmlType="submit"
          >
            创建任务
          </Button>
          <Button onClick={onClose}>
            取消
          </Button>
        </Form.Item>
      </Form>
    </Drawer>
  );
};

export default DrawerTask;

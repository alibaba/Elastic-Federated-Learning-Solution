import React, { useState, useRef, useEffect } from 'react';
import { LogoutOutlined, SettingOutlined, UserOutlined } from '@ant-design/icons';
import { Avatar, Form, Spin, Drawer, Space, Button, message, Input, Radio, Checkbox } from 'antd';
import { useRequest, } from 'ahooks';
import { updateUser } from './service';
import { useModel, history } from 'umi';
import { get, isEmpty } from 'lodash';
import { currentUser as queryCurrentUser } from '@/services/console/api';

const CheckboxGroup = Checkbox.Group;
export type SettingsDrawerProps = {
  settingsVisible: boolean;
  closeSettings: () => void;
};

const SettingsDrawer: React.FC<SettingsDrawerProps> = (props) => {
  const { settingsVisible, closeSettings } = props;
  const [form] = Form.useForm();
  const permissionOptions = [
    {label: '运行权限', value: 'runPermission'}, 
    {label: '新建权限', value: 'addTaskPermission'},
  ];
  const { initialState, setInitialState } = useModel('@@initialState');
  const [currentUser, setCurrentUser] = useState(initialState?.currentUser);

  // update
  const { loading, run: update } = useRequest(updateUser, {
    manual: true,
    onSuccess: (result, params) => {
      const { rsp_code, data, message: msg } = result;
      if (rsp_code === 0) {
        message.success('操作成功!', 1, closeSettings);
        setInitialState((state) => ({ ...state, currentUser: data }));
        if (get(params[0], 'password')) {
          history.push('/user/login');
        }
      } else {
        message.error(msg);
      }
    },
  });

  useEffect(() => {
    getUserInfo();
  }, [initialState]);

  useEffect(() => {
    if (settingsVisible && !isEmpty(currentUser)) {
      form.setFieldsValue({
        ...createInitialFormValues(),
      });
    } else {
      form.resetFields();
    };
  }, [settingsVisible, currentUser]);

  const getUserInfo = async () => {
    const res = await queryCurrentUser();
    setCurrentUser(res.data);
  }

  const createInitialFormValues = () => {
    const {role, info} = currentUser;
    if (!isEmpty(info)) {
      const {phone, email, permission: _permission} = info;
      const permission = [];
      for(const key in _permission) {
        _permission[key] === true && permission.push(key);
      }
      return {
        phone,
        email,
        role,
        permission
      };
    } else {
      return {
        role
      }
    }
  }

  const formLayuot = {
    labelCol: {
      span: 4,
    },
    wrapperCol: {
      span: 19,
    }
  };

  const submitFormValue = () => {
    const {origin_password, password, phone, email, role, permission: _permission} = form.getFieldsValue();
    const permission = {
      runPermission: _permission.includes('runPermission') ? true : false,
      addTaskPermission: _permission.includes('addTaskPermission') ? true : false
    }
    const params = {
      ...currentUser,
      origin_password,
      password,
      role,
      info: {
        permission,
        phone,
        email
      }
    }
    update(params);
  }

  return (
    <Drawer width="40%" visible={settingsVisible} title="个人设置" placement="right" onClose={closeSettings}

      footer={
        <div style={{ textAlign: "end" }}>
          <Space>
            <Button onClick={closeSettings}>取消</Button>
            <Button type="primary" onClick={() => {submitFormValue() }}>
              提交
        </Button>
          </Space>
        </div>
      }
    >
      <Form
        form={form}
        {...formLayuot}
        onFinish={(values: any) => {

        }}
      >
        <Form.Item name="origin_password" label="旧密码">
          <Input.Password placeholder="input password" />
        </Form.Item>
        <Form.Item 
          name="password" 
          label="新密码" 
          dependencies={['origin_password']}
          rules={[
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (value && getFieldValue('origin_password') === value) {
                  return Promise.reject(new Error('新密码不能与旧密码相同!'));
                }
                return Promise.resolve();
              },
            }),
          ]}
        >
          <Input.Password placeholder="input password" />
        </Form.Item>
        <Form.Item name="phone" label="联系电话">
          <Input />
        </Form.Item>
        <Form.Item 
          name="email" 
          label="邮箱"
          rules={[
            {
              type: 'email',
              message: '输入正确的email!',
            },
          ]}
        >
          <Input />
        </Form.Item>
        <Form.Item name="permission" label="权限" initialValue={['runPermission', 'addTaskPermission']} >
          <CheckboxGroup options={permissionOptions} />
        </Form.Item>
        <Form.Item name="role" label="角色" >
          <Radio.Group>
            <Radio value={0}>root</Radio>
            <Radio value={1}>admin</Radio>
            <Radio value={2}>user</Radio>
          </Radio.Group>
        </Form.Item>
      </Form>
    </Drawer>
  );
};

export default SettingsDrawer;
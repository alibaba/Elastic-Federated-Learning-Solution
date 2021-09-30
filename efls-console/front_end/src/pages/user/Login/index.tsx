import {
  AlipayCircleOutlined,
  LockOutlined,
  MobileOutlined,
  TaobaoCircleOutlined,
  UserOutlined,
  WeiboCircleOutlined,
} from '@ant-design/icons';
import { Alert, Space, message, Tabs } from 'antd';
import React, { useState, useRef } from 'react';
import type { FormInstance } from 'antd';
import ProForm, { ProFormCaptcha, ProFormCheckbox, ProFormText, ProFormSelect } from '@ant-design/pro-form';
import { useIntl, Link, history, FormattedMessage, SelectLang, useModel } from 'umi';
import { login, register } from './service';
import styles from './index.less';

const LoginMessage: React.FC<{ content: string; }> = ({ content }) => (
  <Alert
    style={{
      marginBottom: 24,
    }}
    message={content}
    type="error"
    showIcon
  />
);

const Login: React.FC = () => {
  const [submitting, setSubmitting] = useState(false);
  const [userLoginState, setUserLoginState] = useState<API.LoginResult>({});
  const [type, setType] = useState<string>('account');
  const { initialState, setInitialState } = useModel('@@initialState');
  const formRef = useRef<FormInstance>();


  const intl = useIntl();


  const handleType = (type: string = 'account') => {
    setType(type);
    setUserLoginState({});
    formRef.current?.resetFields();
  };

  const handleSubmit = async (values: API.LoginParams) => {
    setSubmitting(true);
    const params = {
      name: values?.username,
      password: values?.password,
    };
    let submitService = login;
    if (type !== "account") {
      submitService = register;
      params['role'] = values?.role;
    };


    try {
      // 登录
      const msg = await submitService(params);
      if (type == "account") {
        if (msg.rsp_code === 0) {
          const defaultLoginSuccessMessage = intl.formatMessage({
            id: 'pages.login.success',
            defaultMessage: '登录成功！',
          });
          message.success(defaultLoginSuccessMessage);
          const userInfo = {
            ...msg?.data,
            name: msg?.data?.name ?? '',
            userid: msg?.data?.id ?? '',
          };
          await setInitialState((s) => ({
            ...s,
            currentUser: userInfo,
          }))
          history.push('/projects');
          return;
        };

      } else {
        if (msg.rsp_code === 0) {
          const defaultLoginSuccessMessage = intl.formatMessage({
            id: 'success',
            defaultMessage: '注册成功！',
          });
          message.success(defaultLoginSuccessMessage);
          setSubmitting(false);
          handleType();
          return;
        }
      };
      const msgerr = {
        status: rsp_code !== 0 && 'err',
        info: message
      }
      // 如果失败去设置用户错误信息
      type === "account" && setUserLoginState(msgerr);
    } catch (error) {
      const defaultLoginFailureMessage = intl.formatMessage({
        id: 'failure',
        defaultMessage: '操作失败，请重试！',
      });
      message.error(defaultLoginFailureMessage);
      type === "account" && setUserLoginState({ status: 'err' });
    }
    setSubmitting(false);
  };
  const { status, type: loginType } = userLoginState;

  return (
    <div className={styles.container}>
      <div className={styles.lang} data-lang>
        {SelectLang && <SelectLang />}
      </div>
      <div className={styles.content}>
        <div className={styles.top}>
          <div className={styles.header}>
            <Link to="/">
              <span className={styles.title}>Elastic Federated Learning Platform</span>
            </Link>
          </div>
          <div className={styles.desc}>
            <p>兼收并蓄，博采众长，打造极致AI</p>
          </div>
        </div>

        <div className={styles.main}>
          <ProForm
            formRef={formRef}
            initialValues={{
              autoLogin: true,
            }}
            submitter={{
              searchConfig: {
                submitText: type == 'account' ? '登录' : '注册',
              },
              render: (_, dom) => dom.pop(),
              submitButtonProps: {
                loading: submitting,
                size: 'large',
                style: {
                  width: '100%',
                },
              },
            }}
            onFinish={async (values) => { handleSubmit(values as API.LoginParams); }}
            style={{ width: 360 }}
          >
            <Tabs activeKey={type} onChange={(key) => handleType(key)}>
              <Tabs.TabPane
                key="account"
                tab="账号登录"
              />
              <Tabs.TabPane
                key="register"
                tab="账号注册"
              />
            </Tabs>

            {status == 'err' && type == 'account' && (
              <LoginMessage
                content={intl.formatMessage({
                  id: 'errorMessage',
                  defaultMessage: '账户或密码错误/不存在',
                })}
              />
            )}

            {type === 'account' && (
              <>
                <ProFormText
                  name="username"
                  fieldProps={{
                    size: 'large',
                    prefix: <UserOutlined className={styles.prefixIcon} />,
                  }}
                  placeholder="用户名"
                  rules={[
                    {
                      required: true,
                      message: (
                        <FormattedMessage
                          id="pages.login.username.required"
                          defaultMessage="请输入用户名!"
                        />
                      ),
                    },
                  ]}
                />

                <ProFormText.Password
                  name="password"
                  fieldProps={{
                    size: 'large',
                    prefix: <LockOutlined className={styles.prefixIcon} />,
                  }}
                  placeholder="密码"
                  rules={[
                    {
                      required: true,
                      message: (
                        <FormattedMessage
                          id="pages.login.password.required"
                          defaultMessage="请输入密码！"
                        />
                      ),
                    },
                  ]}
                />

                <div style={{ marginBottom: 24, }}>
                  <ProFormCheckbox noStyle name="autoLogin">
                    <FormattedMessage id="pages.login.rememberMe" defaultMessage="自动登录" />
                  </ProFormCheckbox>
                  <a style={{ float: 'right', }} >
                    <FormattedMessage id="pages.login.forgotPassword" defaultMessage="忘记密码" />
                  </a>
                </div>
              </>
            )}

            {type === 'register' && (
              <>
                <ProFormText
                  name="username"
                  fieldProps={{
                    size: 'large',
                    prefix: <UserOutlined className={styles.prefixIcon} />,
                  }}
                  placeholder="用户名"
                  rules={[
                    {
                      required: true,
                      message: (
                        <FormattedMessage
                          id="pages.login.username.required"
                          defaultMessage="请输入用户名!"
                        />
                      ),
                    },
                  ]}
                />
                <ProFormText.Password
                  name="password"
                  fieldProps={{
                    size: 'large',
                    prefix: <LockOutlined className={styles.prefixIcon} />,
                  }}
                  placeholder="密码"
                  rules={[
                    {
                      required: true,
                      message: (
                        <FormattedMessage
                          id="pages.login.password.required"
                          defaultMessage="请输入密码！"
                        />
                      ),
                    },
                  ]}
                />
                <ProFormSelect
                  name="role"
                  fieldProps={{ size: 'large', }}
                  placeholder="角色"
                  valueEnum={{
                    0: 'root',
                    1: 'admin',
                    2: 'user',
                  }}
                  rules={[{ required: true, message: '角色是必选项' }]}
                  style={{ height: 40 }}
                />
              </>
            )}

          </ProForm>
        </div>
      </div>
    </div>
  );
};

export default Login;

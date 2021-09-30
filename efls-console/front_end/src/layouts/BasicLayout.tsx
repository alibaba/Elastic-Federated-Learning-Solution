/**
 */
import type {
  MenuDataItem,
  BasicLayoutProps as ProLayoutProps,
  Settings,
} from '@ant-design/pro-layout';
import ProLayout, { DefaultFooter } from '@ant-design/pro-layout';
import { Card } from 'antd';
import React, { useEffect, useState, useContext } from 'react';
import { useRequest } from 'ahooks';
import { useIntl, FormattedMessage, Link, useModel, history } from 'umi';
import RightContent from '@/components/RightContent';
import ProjectContext from "@/utils/ProjectContext";
import ProjectDescriptions from './components/ProjectDescriptions';
import styles from './ProjectLayout.less';
import logo from '../../public/logo.svg';
import { getProjectDetails } from '../pages/projects/service';
import { RootObject } from './data';



export type BasicLayoutProps = {
  breadcrumbNameMap: Record<string, MenuDataItem>;
  route: ProLayoutProps['route'] & {
    authority: string[];
  };
  settings: Settings;
  location: {
    query: {
      projectId: string;
    }
  }
} & ProLayoutProps;

export type BasicLayoutContext = { [K in 'location']: BasicLayoutProps[K] } & {
  breadcrumbNameMap: Record<string, MenuDataItem>;
};

const menuDataRender = (menuList: MenuDataItem[]): MenuDataItem[] =>
  menuList.map((item) => {
    return {
      ...item,
      children: item.children ? menuDataRender(item.children) : undefined,
    };
  });


const BasicLayout: React.FC<BasicLayoutProps> = (props) => {
  const {
    children,
    location = {
      pathname: '/',
      query: {
        projectId: ''
      }
    },
  } = props;
  const { initialState } = useModel('@@initialState');
  const [projectConfig, setProjectConfig] = useState<RootObject>();
  const { formatMessage } = useIntl();

  // console.log('initialState',initialState);
  const projectId = location.query.projectId || initialState?.projectId;
  const { loading, run: get_project_details } = useRequest(getProjectDetails, {
    manual: true,
    onSuccess: (result, params) => {
      const { data, rsp_code } = result;
      if (rsp_code === 0 && Object.keys(data).length > 0) {
        setProjectConfig(data);
      };
    },
  });

  useEffect(() => {
    if (projectId) {
      get_project_details(projectId);
    }
    // else {
    //   history.push('/');
    // };
  }, [projectId]);

  return (
    <ProLayout
      className={styles.basicLayout}
      logo={logo}
      formatMessage={formatMessage}
      {...props}
      layout='mix'
      navTheme='light'
      style={{ paddingTop: '14px' }}
      contentWidth='Fluid'
      title={`Elastic Federated Learning Platform`}
      // onCollapse={handleMenuCollapse}
      onMenuHeaderClick={() => history.push('/')}
      menuItemRender={(menuItemProps, defaultDom) => {
        if (
          menuItemProps.isUrl ||
          !menuItemProps.path ||
          location.pathname === menuItemProps.path
        ) {
          return defaultDom;
        }
        return <Link to={{ pathname: menuItemProps.path, search: `?projectId=${projectId}` }}>{defaultDom}</Link>;
      }}
      breadcrumbRender={(routers = []) => [
        {
          path: '/',
          breadcrumbName: formatMessage({ id: 'menu.home' }),
        },
        ...routers,
      ]}
      itemRender={(route, params, routes, paths) => {
        const first = routes.indexOf(route) === 0;
        return first ? (
          <Link to={paths.join('/')}>{route.breadcrumbName}</Link>
        ) : (
            <span>{route.breadcrumbName}</span>
          );
      }}
      // footerRender={() => defaultFooterDom}
      menuDataRender={menuDataRender}
      rightContentRender={() => <RightContent />}
    >
      <ProjectContext.Provider value={{ projectConfig: projectConfig }}>
        <ProjectDescriptions />
        <Card bordered={false} className={styles.cardBody} >
          {children}
        </Card>
      </ProjectContext.Provider>
    </ProLayout >
  );
};

export default BasicLayout;
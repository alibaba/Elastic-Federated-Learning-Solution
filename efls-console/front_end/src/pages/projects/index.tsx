import React, { useState, useRef, useEffect } from 'react';
import { history, useModel } from 'umi';
import { useRequest } from 'ahooks';
import { Button, Card, Col, Row, Statistic, Badge, Tag, Tooltip, Empty } from 'antd';
import { ReloadOutlined, PlusCircleOutlined, SettingOutlined } from '@ant-design/icons';
import CardContainer from './components/CardContainer';
import DrawerForm from './components/DrawerForm';
import styles from './styles.less';
import { getProjectList } from './service';
import { ProjectConfig } from './data';

const Projects: React.FC = () => {
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [projectInfo, setProjectInfo] = useState({});
  const [project, setProject] = useState([]);
  const { initialState, setInitialState } = useModel('@@initialState');
  const { loading, run: get_project_list } = useRequest(getProjectList, {
    manual: true,
    onSuccess: (result, params) => {
      const { data: { project_list = [] }, rsp_code } = result;
      if (rsp_code === 0 && project_list.length > 0) {
        setProject(project_list);
      };
    },
  });

  useEffect(() => {
    get_project_list();
  }, []);

  const onClose = () => {
    setDrawerVisible(!drawerVisible);
  };

  const renderProjectTitleStatus = (record: ProjectConfig) => {
    const title = <span style={{ marginRight: 8 }}>{record.name}</span>;
    const status = record.status;
    let tagStatus;
    switch (status) {
      case 0:
        tagStatus = <Tag color="default">DRAFT</Tag>
        break;
      case 1:
        tagStatus = <Tag color="success">READY</Tag>
        break;
      case 2:
        tagStatus = <Tag color="warning">ARCHIVE</Tag>
        break;
    };
    return <span>{[title, tagStatus]}</span>
  };

  const showDrawer = (data: ProjectConfig) => {

    setProjectInfo({ name: data?.name, id: data?.id });
    setDrawerVisible(!drawerVisible)
  };

  const empty = (<div style={{ lineHeight: '500px', textAlign: 'center', fontSize: '0px', }} >
    <Card className={styles.newAppCard}>
      <a onClick={() => history.push('/projects/add')}><PlusCircleOutlined className={styles.newIcon} /></a>
      <p className={styles.newText}>创建项目</p>
    </Card>
  </div>);
  return (
    <div className={styles.mainDiv}>
      <h2>项目管理</h2>
     
      {/* <Row style={{ marginBottom: 10 }}>
        <Col span={12} style={{ textAlign: "end" }}><Button type="link" onClick={() => get_project_list()}><ReloadOutlined />刷新</Button></Col>
      </Row> */}
      <div>
        {project.length > 0 ?
          <Row gutter={[8, 8]}>
            <Col span={6} >
              <Card className={styles.newAppCard}>
                <a onClick={() => history.push('/projects/add')}><PlusCircleOutlined className={styles.newIcon} /></a>
                <p className={styles.newText}>创建项目</p>
              </Card>
            </Col>
            {
              project.map((r: ProjectConfig) =>
                <Col span={6} key={r.id}>
                  <div className={styles.project_container}
                    onClick={(e) => {
                      e.preventDefault();
                      if (initialState)
                        initialState.projectId = r.id;
                      setInitialState(initialState);
                      history.push(`/app/task/train?projectId=${r.id}`);
                    }}
                  >
                    <Card title={<>{renderProjectTitleStatus(r)}</>}
                      extra={<Tooltip title="设置项目信息">
                        <Button shape="circle"
                          onClick={(e) => {

                            e.stopPropagation();
                            showDrawer(r);
                          }}
                          icon={<SettingOutlined />} />
                      </Tooltip>}
                      hoverable>
                      <CardContainer projectInfo={r} showDrawer={showDrawer} />
                    </Card>
                  </div>
                </Col>)}
          </Row>
          : empty}
      </div>
      <DrawerForm visible={drawerVisible} onClose={onClose} projectInfo={projectInfo} refreshProject={get_project_list} />
    </div >
  );
};

export default Projects;

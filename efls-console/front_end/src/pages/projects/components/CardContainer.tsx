import React, { useState, useRef, useEffect } from 'react';
import moment from 'moment';
import { useRequest } from 'ahooks';
import { Button, Card, Col, Row, Statistic, Badge, Tag, Tooltip } from 'antd';
import { FundProjectionScreenOutlined, ApiOutlined, ToolOutlined } from '@ant-design/icons';
import styles from '../styles.less';
import { getProjectConnect } from '../service';
import { ProjectConfig } from '../data';


interface CardContainerProps {
  projectInfo: ProjectConfig;
  showDrawer: (params: ProjectConfig) => void;
};

const CardContainer: React.FC<CardContainerProps> = (props) => {
  const { projectInfo, showDrawer } = props;
  const [connectStatus, setConnectStatus] = useState(0);
  const { loading, run: get_project_connect } = useRequest(getProjectConnect, {
    manual: true,
    onSuccess: (result, params) => {
      const { rsp_code, data: { project_id } } = result;
      if (rsp_code === 0 && project_id) {
        setConnectStatus(1);
      } else {
        setConnectStatus(2);
      };
    },
  });

  const inspectProjectStatus = () => {
    get_project_connect(projectInfo?.id);
  };

  const renderConnectStatus = () => {
    switch (connectStatus) {
      case 1:
        return <Badge status='success' text="成功" />
      case 2:
        return <Badge status='error' text="失败" />
      default:
        return <Badge status='processing' text="待检查" />
    };
  };



  return (
    <div>
      <div className={styles.card_body}>
        {/* <div className={styles.card_div} >
          <Statistic title="工作流任务数量" value={projectInfo.num_workflow} />
        </div> */}
        <div className={styles.card_div}>
          {projectInfo.comment}
        </div>
      </div>
      <Row className={styles.card_footer} onClick={(e) => e.stopPropagation()}>
        <Col flex="1 1 150px" key={"time"}>
          <p>
            <span className={styles.card_span} >链接状态:</span><span style={{paddingLeft:'1em'}}>{renderConnectStatus()}</span>
          </p>
        </Col>
        <Col flex="0 1 100px" style={{ textAlign: 'end' }}>
            <Button  size= "small" type="primary" icon={<ApiOutlined />} shape="round" loading={loading} onClick={inspectProjectStatus}>检查连接</Button>
            {/* <Button type="text"  size="small" icon={<ToolOutlined />} style={{ ...btnStyle }} onClick={() => showDrawer(projectInfo)}>更新配置</Button> */}
        </Col>
      </Row>
    </div >
  );
};

export default CardContainer;

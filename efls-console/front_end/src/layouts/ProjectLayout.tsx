import ProLayout from '@ant-design/pro-layout';
import React, { useEffect, useState } from 'react';
import RightContent from '@/components/RightContent';
import styles from './ProjectLayout.less';

const ProjectLayout: React.FC = props => {
  const { children } = props;
  return (
    <ProLayout
      className={styles}
      layout="top"
      title={`Elastic Federated Learning Platform`}
      rightContentRender={() => (<RightContent />)}
      {...props}
    >
      {children}
    </ProLayout>
  );
};

export default ProjectLayout;

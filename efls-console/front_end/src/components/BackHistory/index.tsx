
import React, { FC, } from 'react';
import { history } from 'umi';
import { LeftOutlined } from '@ant-design/icons';

interface BackProps {
  className?: string;
  backString?: string;
  goBackFunc?: () => void;
  goBackUrl?: string;
  disabled?: boolean;
}

const BackHistory: FC<BackProps> = (props:any) => {
  const { 
    className, backString = '返回', goBackUrl = null, disabled = false, goBackFunc,
  } = props;
  return (
    <a 
      className={className} 
      onClick={() => {
        if (!!goBackFunc) {
          goBackFunc();
        } else {
          !goBackUrl ?
          history.goBack() :
          history.push(goBackUrl)
        }
      }}
      style={{ marginRight: 12 }}
      disabled={!!disabled}
    >
      <LeftOutlined />{backString}
    </a>
  );
}

export default BackHistory;
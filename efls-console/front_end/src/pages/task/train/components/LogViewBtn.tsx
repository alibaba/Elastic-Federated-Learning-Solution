import React, { useState, useRef, useEffect } from 'react';
import { Button, Modal } from 'antd';

interface LogViewBtnProps {
  log: string;
};

const LogViewBtn: React.FC<LogViewBtnProps> = (props) => {
  const { log } = props;
  const [msg, setMsg] = useState('');
  const [isModalVisible, setIsModalVisible] = useState(false);

  const showModal = (test: string) => {
    setIsModalVisible(!isModalVisible);
    setMsg(test);
  };

  const handleCancel = () => {
    setIsModalVisible(false);
  };

  const btnStyle = { margin: '0px 6px', padding: 0, height: 20 };
  const preStyle = {
    width: '100%',
    height: '60vh',
    backgroundColor: 'rgb(51, 51, 51)',
    color: 'white',
    fontSize: '16px',
    wordBreak: 'break-word',
    whiteSpace: 'pre-wrap'
  };

  const logBtn = () => {
    let jsonLog;
    const btnAry = [];
    try {
      jsonLog = JSON.parse(log);
    } catch (error) {
      console.error('转换失败')
    }
    if (!!jsonLog) {
      for (const key in jsonLog) {
        const text = jsonLog[key] || '暂无数据';
        const btn = <Button type='link' style={btnStyle} onClick={() => showModal(text)} >{key}</Button>;
        btnAry.push(btn);
      };
    };
    return btnAry;
  };

  const btnAry = logBtn();
  if (!log || btnAry.length == 0) {
    return <>暂无日志</>
  };

  return (
    <>
      {btnAry}
      <Modal visible={isModalVisible} width={'85%'} footer={false} onCancel={handleCancel}>
        <div style={{ minHeight: '100%', width: '100%', marginTop: '22px' }}>
          <pre style={preStyle}>
            {msg}
          </pre>
        </div>
      </Modal>
    </>
  );
};

export default LogViewBtn;
import React, { useState, useRef, useEffect, useContext } from 'react';
import { Rate, Tooltip } from 'antd';
import ProjectContext from "@/utils/ProjectContext";

interface MyCollectionProps {
  namespace: string;
  record: any;
  myCollectionChangeCallback?: () => void;
};

const MyCollection: React.FC<MyCollectionProps> = (props) => {
  const { record, myCollectionChangeCallback = () => { }, namespace } = props;
  const { projectConfig } = useContext(ProjectContext);
  const id = record?.id;
  const CACHE_KEY = `fl-${projectConfig.name}-${namespace}`;
  const myCollectionList = JSON.parse(localStorage.getItem(CACHE_KEY) ?? '[]');
  const [value, setValue] = useState(myCollectionList?.includes(id) ? 1 : 0);

  const setMyCollectionListCached = () => {
    let newMyCollectionList = [...myCollectionList];
    if (!!newMyCollectionList.includes(id)) {
      newMyCollectionList = myCollectionList.filter(r => r !== id);
    } else {
      newMyCollectionList.push(id);
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(newMyCollectionList));
  };

  const changeMyCollection = (value: any) => {
    setValue(value);
    setMyCollectionListCached();
    myCollectionChangeCallback();
  };

  const desc = !!value ? '取消收藏' : '收藏';
  return (<Tooltip placement="right" title={desc}>
    <span onClick={(e: any) => { e.stopPropagation() }}>
      <Rate onChange={(val) => { changeMyCollection(val) }} value={value} count={1} style={{ marginLeft: 8, fontSize: 16 }} />
    </span>
  </Tooltip>
  );

};

export default MyCollection;
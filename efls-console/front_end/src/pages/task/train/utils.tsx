import { Badge, Button, Divider, Popconfirm, Tooltip } from 'antd';
import { history } from 'umi';
import { ReactElement } from '_@types_react@17.0.21@@types/react';

const renderStatus = (status: number) => {
  switch (status) {
    case 0:
      return <Badge status="default" text="DRAFT" />
    case 1:
      return <Badge color="blue" text="READY" />
    case 2:
      return <Badge color="red" text="ARCHIVE" />

    default:
      return <Badge status="default" text="--" />
  };
};

const renderInstanceStatus = (status: number) => {
  switch (status) {
    case 0:
      return <Badge status="default" text="DRAFT" />
    case 1:
      return <Badge color="blue" text="READY" />
    case 2:
      return <Badge color="red" text="ARCHIVE" />
    case 3:
      return <Badge color="blue" text="RUNNING" />
    case 4:
      return <Badge color="red" text="FAILED" />
    case 5:
      return <Badge color="red" text="TERMINATED" />

    default:
      return <Badge status="default" text="--" />
  };
};

const renderAction = (record: any, pairTaskInter: (id: string) => void, versionStart: (params: any) => void, showDrawer: (info: any) => void, projectId: string) => {
  const text = record.task_root ? "配对" : "同步";
  const details = <a onClick={() => history.push(`/app/task/train/details?id=${record.id}&projectId=${projectId}`)}>查看</a>;
  const edit = <a onClick={() => history.push(`/app/task/train/edit?id=${record.id}&projectId=${projectId}`)}>编辑</a>;
  const pair = <Popconfirm title={`确认${text}?`} onConfirm={() => pairTaskInter(record.id)} okText="确认" cancelText="取消"><a>{text}</a></Popconfirm>;
  const run = <Popconfirm title="确认运行?" onConfirm={() => versionStart(record.task_inter_id)} okText="确认" cancelText="取消"><a>运行</a></Popconfirm>;
  const version = <a onClick={() => history.push(`/app/task/train/add?id=${record.id}`)}>生成版本</a>;
  const divider = <Divider type="vertical" />;
  const resources = <a onClick={() => { showDrawer(record) }}>资源上传</a>;
  switch (record.status) {
    case 0:
      // return record.type === 1 ? <>{[edit, divider, pair, divider, resources]}</> : <>{[edit, divider, pair]}</>
      return <>{[edit, divider, pair, divider, resources]}</>
    case 1:
    case 2:
      const action = !record.task_root ? [details, divider, run, divider, resources] : [details, divider, run, divider, version, divider, resources];
      return action;
  };
}

const renderInstanceAction = (record: any, handleInstanceRun: (params: any) => void, handleInstanceUpdate: (id) => void): ReactElement => {
  const start = (<Popconfirm title="确认启动?" onConfirm={() => handleInstanceRun({ id: record.id, operation: 0 })} okText="确认" cancelText="取消">
    <a>启动</a>
  </Popconfirm>);
  const stop = (<Popconfirm title="确认停止?" onConfirm={() => handleInstanceRun({ id: record.id, operation: 1 })} okText="确认" cancelText="取消">
    <a>停止</a>
  </Popconfirm>);
  const divider = <Divider type="vertical" />;
  const update = <a onClick={() => handleInstanceUpdate(record.id)}>配对</a>
  switch (record.status) {
    case 0:
      return <>{update}</>
    case 1:
      return <>{[start, divider, stop]}</>;
    case 3:
      return <>{stop}</>;
    case 5:
      return <>{start}</>;
    default:
      return;
  };
};

//训练任务columns
export const TrainTaskTableColumns = [
  {
    title: '任务名称',
    dataIndex: 'name',
    render: (dom, entity) => {
      return (
        <a onClick={() => { }}>{dom}</a>
      );
    },
  },
  {
    title: '隶属项目',
    dataIndex: 'project_name',
    hideInTable: true,
  },
  {
    title: 'id',
    dataIndex: 'id',
    key: 'id',
    hideInTable: true,
  },
];

export const TrainVersionTableColumns = (pairTaskInter: (id: string) => void, versionStart: (params: any) => void, showDrawer: (info: any) => void, projectId: string) => [
  { title: 'version', dataIndex: 'version', key: 'version', width: 150, fixed: 'left' },
  {
    title: '隶属项目',
    dataIndex: 'project_name',
    width: 100,
  },
  {
    title: 'user',
    dataIndex: 'owner_name',
    hideInSearch: true,
    width: 100,
  },
  {
    title: 'comment',
    dataIndex: 'comment',
    key: 'comment',
    hideInSearch: true,
    width: 200,
    ellipsis: {
      showTitle: false,
    },
    render: (val: any) => (
      val ? <Tooltip placement={'topLeft'} title={val}>
        {val}
      </Tooltip> : '--'
    ),
  },
  {
    title: '状态',
    dataIndex: 'status',
    render: (val) => renderStatus(val),
    width: 120,
  },
  {
    title: '操作',
    dataIndex: 'operation',
    key: 'operation',
    width: 140,
    fixed: 'right',
    render: (val: any, record: any) => renderAction(record, pairTaskInter, versionStart, showDrawer, projectId),
  },
];

export const TrainInstanceTableColumns = (handleInstanceRun: (params: any) => void, handleInstanceUpdate: (id: boolean) => void, projectId: string) => [
  {
    title: 'instanceId',
    dataIndex: 'id',
    key: 'id',
    width: '100px',
    render: (val: string) => <a onClick={() => history.push(`/app/task/train/instance?id=${val}&projectId=${projectId}`)}>{val}</a>
  },
  {
    title: 'status',
    dataIndex: 'status',
    width: '200px',
    render: (val: number) => renderInstanceStatus(val),
  },
  {
    title: '操作',
    dataIndex: 'operation',
    key: 'operation',
    width: '200px',
    render: (val: any, record: any) => renderInstanceAction(record, handleInstanceRun, handleInstanceUpdate),
  },
];
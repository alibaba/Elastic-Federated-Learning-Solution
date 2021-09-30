import { request } from 'umi';
import { get, post, put} from '@/utils/request';


//task名字校验
export async function getTaskName(params:any) {
  return get(`/task/name/${params}`,null);
};

//获取任务列表
export async function getInformationTaskList(params:any) {
  return get('/task/list', params);
};

//创建任务
export async function createInformationTask(params:any, options?: { [key: string]: any }) {
  return post('/task', params);
};

//更新我方配置
export async function updateInformationTask(params:any,options?: any) {
  const id = params.id;
  delete params["id"];
  return put(`/task/${id}`,params);
};

//获取我方配置
export async function getInformationTaskIntraInfo(params:any,options?: any) {
  return get(`/task/${params}`,null);
};

//获取对方配置
export async function getInformationTaskInterInfo(params:any,options?: any) {
  return get(`/task/inter/${params}`,null);
};

// 配对接口
export async function createInformationTaskInter(params:any,options?: any) {
  return post(`/task/inter/${params}`,null);
};

//获取instance列表
export async function getInformationTaskInstanceList(params:any,options?: any) {
  return get('/task_instance/list',params);
};

//task_instance 启动/停止
export async function informationTaskInstanceStatus(params:any,options?: any) {
  return post(`/task_instance/status/${params.id}`,params);
};

//task_instance 详情
export async function getInformationTaskInstanceDetails(id:any,options?: any) {
  return get(`/task_instance/${id}`,null);
};

//task_instance 运行
export async function instanceInformationTaskRun(id:any,options?: any) {
  return post(`/task_instance/${id}`,null);
};

//instance 更新
export async function instanceInformationTaskUpdate(params:any,options?: any) {
  const id = params.id;
  delete params["id"];
  return put(`/task_instance/${id}`,params);
};


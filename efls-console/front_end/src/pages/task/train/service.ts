import { request } from 'umi';
import { get, post, put, del} from '@/utils/request';

//task名字校验
export async function getTaskName(params:any) {
  return post(`/task/name/${params}`,null);
};

//获取任务列表
export async function getTaskList(params:any) {
  return get('/task/list',params);
};

//创建任务
export async function createTask(params:any, options?: { [key: string]: any }) {
  return post('/task',params);
};

//更新我方配置
export async function updateTask(params:any,options?: any) {
  const id = params.id;
  delete params["id"];
  return put(`/task/${id}`,params);
};

//获取我方配置
export async function getTaskIntraInfo(params:any,options?: any) {
  return get(`/task/${params}`,null);
};

//获取对方配置
export async function getTaskInterInfo(params:any,options?: any) {
  return get(`/task/inter/${params}`,null);
};

// 配对接口
export async function createTaskInter(params:any,options?: any) {
  return post(`/task/inter/${params}`,null);
};

//获取instance列表
export async function getTaskInstanceList(params:any,options?: any) {
  return get('/task_instance/list',params);
};

//task_instance 启动/停止
export async function taskInstanceStatus(params:any,options?: any) {
  return post(`/task_instance/status/${params.id}`,params);
};

//task_instance 详情
export async function getTaskInstanceDetails(id:any,options?: any) {
  return get(`/task_instance/${id}`,null);
};

//task_instance 运行
export async function instanceTaskRun(id:any,options?: any) {
  return post(`/task_instance/${id}`,null);
};

//instance 更新
export async function instanceTaskUpdate(params:any,options?: any) {
  const id = params.id;
  delete params["id"];
  return put(`/task_instance/${id}`,params);
};

//上传资源
export async function uploadResources(params:any,options?: any) {
  return post('/resource',params);
};

//删除资源对象
export async function deleteResourcesObj(params:any,options?: any) {
  return del(`/resource/object?name=${params}`,params);
};

//删除资源
export async function deleteResources(id:any,options?: any) {
  return del(`/resource/${id}`,null);
};

//下载资源
export async function downloadResources(name:any,options?: any) {
  return get(`/resource/object?name=${name}`,null);
};

//获取资源列表
export async function queryResourcesList(id:any,options?: any) {
  return get(`/resource/list/${id}`,null);
};

import { request } from 'umi';
import { get, post, put} from '@/utils/request';

export async function getProjectList() {
  return get('/project/list',null);
};

export async function createProject(params:any) {
  return post('/project',params);
};

export async function updateProject(params:any) {
  return put(`/project/${params.id}`,params);
};

export async function getProjectDetails(id: any) {
  return get(`/project/${id}`,null);
};

export async function getProjectConnect(id: any) {
  return get(`/project/connect/${id}`,null);
};

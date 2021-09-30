import { post} from '@/utils/request';

//登录
export async function login(params:any,options?: any) {
  return post('/user/session',params);
}
//注册
export async function register(params:any,options?: any) {
  return post('/user',params);
}

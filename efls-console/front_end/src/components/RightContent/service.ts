import { put } from '@/utils/request';

export async function updateUser(params: any, options?: any) {
  return put(`/user/${params.id}`, params);
}

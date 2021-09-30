import { request } from 'umi';

const EnvDaily = 'daily';
const EnvOnline = 'online';
const MockUrl = '';

// mock url中用各个模块名称 ?mock=mdc,odl
enum moduleNameEnum {
  project = 'project',
  task = 'task',
};

// 获取url地址
export function getCurrentFullUrl() {
  return window.location.href;
};

// 获取环境
export function getEnv() {
  const url = getCurrentFullUrl();
  if (url.indexOf('alimama.net:') > 0) {
    return EnvOnline;
  } else {
    return EnvDaily;
  };
};

export function getBaseUrl() {
  const envName = getEnv();
  if (isMockUrl(moduleNameEnum.project)) {
    return MockUrl;
  };
  switch (envName) {
    case EnvOnline:
      return '';
    default:
      return '';
    // return "http://100.82.84.137:31000";
  };
};

function isMockUrl(modeName: string): boolean {
  let isMocked = false;
  const mockParam = getSearchParam('mock');
  if (String(mockParam).toLowerCase().indexOf(modeName) > -1) {
    isMocked = true;
  };
  return isMocked;
};

// 获取url中search部分的key
export function getSearchParam(key?: string): any {
  const searchStr: string = window.location.search.toString().substr(1);
  if (searchStr === '') {
    return null;
  }
  const searchParams = searchStr.split('&').reduce((previous, current) => {
    const [key, value] = current.split('=');
    previous[key] = decodeURIComponent(value);
    return previous;
  }, {});
  if (key) {
    return searchParams[key];
  } else {
    return searchParams;
  };
};

export function get(url: string, params: any) {
  return request<any>(url, {
    method: 'GET',
    params: { ...params },
    prefix: getBaseUrl(),
    credentials: 'include',
  });
};

export function post(url: string, params: any, options?: any) {
  return request<any>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    data: params,
    ...(options || {}),
    prefix: getBaseUrl(),
    credentials: 'include',
  });
};

export function put(url: string, params: any, options?: any) {
  return request<any>(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    data: params,
    ...(options || {}),
    prefix: getBaseUrl(),
    credentials: 'include',
  });
};

export function del(url: string, params: any, options?: any) {
  return request<any>(url, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
    data: params,
    ...(options || {}),
    prefix: getBaseUrl(),
    credentials: 'include',
  });
};

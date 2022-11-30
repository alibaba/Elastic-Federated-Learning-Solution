import { get } from "lodash";
/**
 * @see https://umijs.org/zh-CN/plugins/plugin-access
 * */
export default function access(initialState: { currentUser?: API.CurrentUser | undefined }) {
  const { currentUser } = initialState || {};
  const canAddTask = get(currentUser, 'info.permission.addTaskPermission', true);
  const canRun = get(currentUser, 'info.permission.runPermission', true);
  return {
    canAdmin: currentUser && currentUser.access === 'admin',
    canRoot: currentUser && currentUser.role === 0,
    canAddTask,
    canRun,
  };
}

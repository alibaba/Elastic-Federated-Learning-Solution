export default [
  {
    path: '/user',
    layout: false,
    routes: [
      {
        path: '/user',
        routes: [
          {
            name: 'login',
            path: '/user/login',
            component: './user/Login',
          },
        ],
      },
      {
        component: './404',
      },
    ],
  },
  
  // {
  //   name: 'list.table-list',
  //   hideInMenu: true,
  //   icon: 'table',
  //   path: '/list',
  //   component: './TableList',
  // },
  {
    name: 'projects',
    icon: 'AppstoreOutlined',
    path: '/projects',
    layout:false,
    hideInMenu: true,
    component:'../layouts/ProjectLayout',
    // component: './projects',
    routes: [
      {
       path: '/projects',
       component: './projects',
      },
      {
       path: '/projects/add',
       component: './projects/addProject',
      },
    ]
  },
  {
    path: '/app',
    redirect: '/app/task/train',
  },
  {
   name:'app',
   path: '/app',
   icon: 'FundProjectionScreenOutlined',
   layout:false,
   component:'../layouts/BasicLayout',
   menu:{
     flatMenu:true,
   },
   routes:[
    {
      name:'task',
      path: '/app/task',
      routes: [
            { 
              name: 'sample',
              path: '/app/task/sample',
              routes:[
                {
                  path: '/app/task/sample',
                  component: './task/information',
                },
                {
                  path: '/app/task/sample/add',
                  component: './task/information/addInformationTask',
                },
                {
                  path: '/app/task/sample/edit',
                  component: './task/information/addInformationTask',
                },
                {
                  path: '/app/task/sample/details',
                  component: './task/information/informationVersionDetails',
                },
                {
                  path: '/app/task/sample/instance',
                  component: './task/information/components/instanceDetails',
                },
              ]
            },
            {
              name: 'train',
              path: '/app/task/train',
              routes: [
                {
                  path: '/app/task/train',
                  component: './task/train',
                },
                {
                  path: '/app/task/train/add',
                  component: './task/train/addTrainTask',
                },
                {
                  path: '/app/task/train/edit',
                  component: './task/train/addTrainTask',
                },
                {
                  path: '/app/task/train/details',
                  component: './task/train/versionDetails',
                },
                {
                  path: '/app/task/train/instance',
                  component: './task/train/components/instanceDetails',
                },
                {
                  component: '404',
                },
              ],
            },
          ],
    },
   ]
  },
  {
    path: '/',
    redirect: '/projects',
  },
  {
    component: './404',
  },
];

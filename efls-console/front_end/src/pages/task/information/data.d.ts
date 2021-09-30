export interface Version {
    comment?: any;
    config: string;
    gmt_create: number;
    gmt_modified: number;
    id: string;
    meta: string;
    name: string;
    owner_id: string;
    owner_name:string;
    project_name:string;
    project_id: string;
    status: number;
    task_inter_id: string;
    task_root: boolean;
    token: string;
    type: number;
    version: string;
}

export interface SampleTaskTableList {
    comment?: any;
    config: string;
    gmt_create: number;
    gmt_modified: number;
    id: string;
    meta: string;
    name: string;
    owner_id: string;
    project_id: string;
    status: number;
    task_inter_id: string;
    task_root: boolean;
    token: string;
    type: number;
    version: Version[];
}

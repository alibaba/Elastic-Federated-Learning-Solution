export interface ProjectConfig {
    comment?: any;
    config: string;
    gmt_create: number;
    gmt_modified: number;
    id: string;
    name: string;
    owner_id: string;
    peer_config: string;
    peer_id: string;
    status: number;
}

export interface ProjectCreateParams {
    name: string;
    peer_url: string;
    config: string;
}

export interface CreateTaskParams {
    config: string;
    meta: string;
    name: string;
    project_id: string;
    task_root: boolean;
    type: number;
}
import React, { useState, useEffect, useRef } from 'react';
import { Button, message, Input, Drawer, Table, Badge, Form, Radio, Upload } from 'antd';
import { UploadOutlined, StarOutlined } from '@ant-design/icons';
import { uploadResources, deleteResourcesObj, deleteResources, downloadResources, queryResourcesList } from '../service';
import { Version } from '../data';

interface EditFormProps {
  onClose: () => void;
  visible: boolean;
  versionInfo: Version;
}

const DrawerResources: React.FC<EditFormProps> = (props) => {
  const { onClose, visible, versionInfo } = props;
  const [ossUploading, setOssUploading] = useState(false);
  const [uploadFlag, setUploadFlag] = useState(false);
  const [fileList, setFileList] = useState([]);

  useEffect(() => {
    if (visible) {
      refreshFileList();
    } else {
      setFileList([]);
    }
  }, [visible]);

  const refreshFileList = () => {
    queryResourcesList(versionInfo.id).then((res: any) => {
      const { rsp_code, data: { resource_list } } = res;
      if (rsp_code === 0) {
        const resourceAry = resource_list.map(r => {
          r["url"] = `/resource/object?name=${r.name}`;
          r["uid"] = r.id;
          return r;
        });
        setFileList(resourceAry);
      }
    });
  };

  console.log(fileList, '===fileList')

  const deleteFileList = (id: string) => {
    setFileList(list => list.filter(r => r.uid !== id));
  };

  const getUpdateProps = () => {
    return {
      data: (dataFile: any) => ({
        name: dataFile.name,
        data: dataFile
      }),
      action: "/resource/object",
      onChange: (info: any) => {
        const { response } = info.file;
        setFileList(info.fileList);
        switch (info.file.status) {
          case 'uploading':
            if (ossUploading === false) {
              setOssUploading(true);
              setUploadFlag(false);
            }
            break;
          case 'done':
            setOssUploading(false);
            if (typeof response == "object" && response.rsp_code == 0) {
              const { uri } = response.data;
              const params = {
                uri,
                task_intra_id: versionInfo.id,
                name: info.file.name
              };
              uploadResources(params).then((res: any) => {
                if (res.rsp_code == 0) {
                  message.success('文件上传成功!');
                  refreshFileList();
                } else {
                  message.error(`文件上传失败! ${response.message}`);
                  deleteFileList(info.file.uid);
                }
              }).catch(err => { message.error(`文件上传失败! ${response.message}`); deleteFileList(info.file.uid); });
            };
            setUploadFlag(true);
            break;
          case 'error':
            setOssUploading(false);
            message.error(`文件上传失败! ${response.message}`);
            deleteFileList(info.file.uid);
            setUploadFlag(false);
            break;
          default:
            break;
        }
      },
      onRemove: (file: any) => {
        const { id } = file;
        deleteResourcesObj(file.name).then((res: any) => {
          if (res.rsp_code == 0) {
            deleteResources(id).then((res: any) => {
              const { rsp_code, data: { result } } = res;
              if (rsp_code == 0 && result) {
                message.success('删除成功!');
                refreshFileList();
              } else {
                message.error('删除失败!');
              };
            });
          };
        });
      },
    };
  };

  const uploadProps = getUpdateProps();

  return (
    <Drawer
      title={`version-${versionInfo.version}`}
      width={720}
      onClose={onClose}
      visible={visible}
    >
      资源附件:  <Upload {...uploadProps} fileList={fileList}>
        <Button icon={<UploadOutlined />}>Upload</Button>
      </Upload>

    </Drawer>
  );
};

export default DrawerResources;

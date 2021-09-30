import React, { FC } from 'react';
import Monaco from '@/components/Monaco';
// import { getEditorLanguage } from '@/utils/nebulaUtils';
import { Alert } from "antd";

interface WSEditorProps {
    content: string;
    fileName: string;
    onChange?: (content: string) => void;
    readOnly?: boolean;
    style?: any;
    saveFunc?: () => void;
}

const WSEditor: FC<WSEditorProps> = props => {
    const { content, fileName, onChange, readOnly = false, style, saveFunc } = props;

    // 设置编辑器的options
    const getOptions = () => ({
        automaticLayout: true, // 100ms interval监听窗口大小
        readOnly: readOnly,
    })

    // 根据文件名的后缀获取当前的编辑器语言
    const getEditorLanguage = (fileName: string) => {
        let lang = 'python';
        if (fileName.endsWith('.py')) {
            lang = 'python';
        } else if (fileName.endsWith('.xml')) {
            lang = 'xml';
        } else if (fileName.endsWith('.json')) {
            lang = 'json';
        } else if (fileName.endsWith('.yaml')) {
            lang = 'yaml';
        }
        return lang;
    };

    return (
        <>
            {
                readOnly &&
                <Alert message="提示：您无权修改本文件！" type="warning" banner style={{ width: "87%", fontSize: "12px", marginBottom: "10px" }} />
            }
            <Monaco
                value={content}
                language={getEditorLanguage(fileName)}
                fontSize={13}
                onChange={onChange}
                options={getOptions()}
                style={{ ...style }}
                saveFunc={saveFunc}
                border={true}
            />
        </>
    );
};

export default WSEditor;
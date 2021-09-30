import React, { FC } from 'react';
import Monaco from '@/components/Monaco';
// import { getEditorLanguage } from '@/utils/nebulaUtils';
import { Alert } from "antd";

interface WSEditorProps {
    fileName: string;
    onChange?: (content: string) => void;
    readOnly?: boolean;
    style?: any;
    saveFunc?: () => void;
    message?: string,
    value?: string;
    className?: string;
    showMessage?: boolean;
}

const WSEditor: FC<WSEditorProps> = props => {
    const { value = '', fileName, showMessage, onChange, className, readOnly = false, style, saveFunc, message = "提示：您无权修改本文件！" } = props;

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

    // 设置编辑器的options
    const getOptions = () => ({
        automaticLayout: true, // 100ms interval监听窗口大小
        readOnly: readOnly,
    })
    const triggerChange = (content: string): void => {
        if (onChange) {
            onChange(content);
        }
    }
    const defaultContent = value;
    return (

        <div style={style}
            className={className}
        >
            {
                (readOnly || showMessage) &&
                <Alert message={message} type="warning" banner style={{ fontSize: "12px", marginBottom: "10px" }} />
            }
            <Monaco
                value={defaultContent}
                language={getEditorLanguage(fileName)}
                fontSize={13}
                onChange={triggerChange}
                options={getOptions()}
                style={{ ...style }}
                saveFunc={saveFunc}
                border={true}
            />
        </div>
    );
};

export default WSEditor;
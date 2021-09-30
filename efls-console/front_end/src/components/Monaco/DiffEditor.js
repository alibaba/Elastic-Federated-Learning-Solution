import * as monaco from 'monaco-editor/esm/vs/editor/editor.api';
import React from 'react';
import PropTypes from 'prop-types';
// import { getNebulaTheme } from '@/utils/nebulaUtils';

export function processSize(size) {
  return !/^\d+$/.test(size) ? size : `${size}px`;
}

// let nebulaTheme = getNebulaTheme();

function noop() { }

const theme = {
  base: 'vs-dark', 
  inherit: true,
  rules: [
    { token: 'custom-info', foreground: 'a3a7a9', background: 'ffffff' },
    { token: 'custom-error', foreground: 'ee4444' },
    { token: 'custom-notice', foreground: '1055af' },
    { token: 'custom-date', foreground: '20aa20' },
  ],
  colors: {
    "editor.background": '#101010'
  }
}

monaco.editor.defineTheme('myTheme', theme)

class DiffEditor extends React.Component {
  constructor(props) {
    super(props);
    this.containerElement = undefined;
    this.__current_value = props.value;
    this.__current_original = props.original;
  }

  componentDidMount() {
    this.initMonaco();
  }

  componentDidUpdate(prevProps) {
    if (
      this.props.value !== this.__current_value ||
      this.props.original !== this.__current_original
    ) {
      // Always refer to the latest value
      this.__current_value = this.props.value;
      this.__current_original = this.props.original;
      // Consider the situation of rendering 1+ times before the editor mounted
      if (this.editor) {
        this.__prevent_trigger_change_event = true;
        this.updateModel(this.__current_value, this.__current_original);
        this.__prevent_trigger_change_event = false;
      }
    }
    if (prevProps.language !== this.props.language) {
      const { original, modified } = this.editor.getModel();
      monaco.editor.setModelLanguage(original, this.props.language);
      monaco.editor.setModelLanguage(modified, this.props.language);
    }
    if (prevProps.theme !== this.props.theme) {
      monaco.editor.setTheme(this.props.theme);
    }
    if (
      this.editor &&
      (this.props.width !== prevProps.width || this.props.height !== prevProps.height)
    ) {
      this.editor.layout();
    }
  }

  componentWillUnmount() {
    this.destroyMonaco();
  }

  editorWillMount() {
    const { editorWillMount } = this.props;
    const options = editorWillMount(monaco);
    return options || {};
  }

  editorDidMount(editor) {
    this.props.editorDidMount(editor, monaco);
    editor.onDidUpdateDiff(() => {
      const value = editor.getModel().modified.getValue();

      // Always refer to the latest value
      this.__current_value = value;

      // Only invoking when user input changed
      if (!this.__prevent_trigger_change_event) {
        this.props.onChange(value);
      }
    });
  }

  updateModel(value, original) {
    const { language } = this.props;
    const originalModel = monaco.editor.createModel(original, language);
    const modifiedModel = monaco.editor.createModel(value, language);
    this.editor.setModel({
      original: originalModel,
      modified: modifiedModel
    });
  }

  initMonaco() {
    const value = this.props.value !== null ? this.props.value : this.props.defaultValue;
    const { original, theme, fontSize, options } = this.props;
    if (this.containerElement) {
      // Before initializing monaco editor
      this.editorWillMount();
      this.editor = monaco.editor.createDiffEditor(this.containerElement, {
        fontSize,
        ...options,
        theme:'vs',
        // theme: nebulaTheme === 'dark' ? 'myTheme' : 'vs',
      });
      if (theme) {
        // monaco.editor.setTheme(theme);
      }
      // After initializing monaco editor
      this.updateModel(value, original);
      this.editorDidMount(this.editor);
    }
  }

  destroyMonaco() {
    if (typeof this.editor !== 'undefined') {
      this.editor.dispose();
    }
  }

  assignRef = (component) => {
    console.log('component = ', component);
    this.containerElement = component;
  };

  render() {
    const { width, height } = this.props;
    const fixedWidth = processSize(width);
    const fixedHeight = processSize(height);
    const style = {
      width: fixedWidth,
      height: fixedHeight
    };

    return <div ref={this.assignRef} style={style} className="react-monaco-editor-container" />;
  }
}

DiffEditor.propTypes = {
  width: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  height: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  original: PropTypes.string,
  value: PropTypes.string,
  fontSize: PropTypes.number,
  defaultValue: PropTypes.string,
  language: PropTypes.string,
  theme: PropTypes.string,
  options: PropTypes.object,
  editorDidMount: PropTypes.func,
  editorWillMount: PropTypes.func,
  onChange: PropTypes.func
};

DiffEditor.defaultProps = {
  width: '100%',
  height: '100%',
  original: null,
  value: null,
  fontSize: 16,
  defaultValue: '',
  language: 'javascript',
  theme: 'myTheme',
  options: {},
  editorDidMount: noop,
  editorWillMount: noop,
  onChange: noop
};

export default DiffEditor;
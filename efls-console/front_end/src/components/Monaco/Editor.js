import * as monaco from 'monaco-editor/esm/vs/editor/editor.api';
import PropTypes from 'prop-types';
import React from 'react';
// import { getNebulaTheme } from '@/utils/nebulaUtils';

export function processSize(size) {
  return !/^\d+$/.test(size) ? size : `${size}px`;
}

// let nebulaTheme = getNebulaTheme();
const nebulaTheme = 'light';

function noop() { }

// refer to https://stackoverflow.com/questions/44766624/custom-background-color-in-monaco-editor
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
    // "editor.background": '#101010',
    "editor.background": '#fff',
  }
}

monaco.editor.defineTheme('myTheme', theme);
monaco.editor.setTheme('myTheme');

class Editor extends React.Component {
  constructor(props) {
    super(props);
    this.containerElement = undefined;
    this.__current_value = props.value;
  }

  componentDidMount() {
    this.initMonaco();
  }

  componentDidUpdate(prevProps) {
    if (this.props.value !== this.__current_value) {
      // Always refer to the latest value
      this.__current_value = this.props.value;
      // Consider the situation of rendering 1+ times before the editor mounted
      if (this.editor) {
        this.__prevent_trigger_change_event = true;
        this.editor.setValue(this.__current_value);
        this.__prevent_trigger_change_event = false;
      }
    }
    if (prevProps.language !== this.props.language) {
      monaco.editor.setModelLanguage(this.editor.getModel(), this.props.language);
    }
    if (prevProps.theme !== this.props.theme) {
      // monaco.editor.setTheme(this.props.theme);
    }
    if (
      this.editor &&
      (this.props.width !== prevProps.width || this.props.height !== prevProps.height)
    ) {
      this.editor.layout();
    }
    if (prevProps.options !== this.props.options) {
      this.editor.updateOptions(this.props.options)
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
    editor.onDidChangeModelContent((event) => {
      const value = editor.getValue();

      // Always refer to the latest value
      this.__current_value = value;

      // Only invoking when user input changed
      if (!this.__prevent_trigger_change_event) {
        this.props.onChange(value, event);
      }
    });

    editor.onDidFocusEditorText(event => {
      const value = editor.getValue();
      this.props.onFocus(value, event);
    })

    editor.onDidBlurEditorText(event => {
      const value = editor.getValue();
      this.props.onBlur(value, event);
    })
  }

  initMonaco() {
    const value = this.props.value !== null ? this.props.value : this.props.defaultValue;
    const { language, theme, fontSize, options, saveFunc } = this.props;
    if (this.containerElement) {
      // Before initializing monaco editor
      Object.assign(options, this.editorWillMount());
      this.editor = monaco.editor.create(this.containerElement, {
        value,
        fontSize,
        language,
        ...options,
        theme:'vs',
      });
      if (theme) {
        // monaco.editor.setTheme(theme);
      }
      // After initializing monaco editor
      this.editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KEY_S, function () {
        if (!!saveFunc) {
          saveFunc();
        }
      });
      this.editorDidMount(this.editor);
    }
  }

  destroyMonaco() {
    if (typeof this.editor !== 'undefined') {
      this.editor.dispose();
    }
  }

  assignRef = (component) => {
    this.containerElement = component;
  };

  render() {
    const { width, height, border } = this.props;
    const fixedWidth = processSize(width);
    const fixedHeight = processSize(height);
    const style = {
      width: fixedWidth,
      height: fixedHeight,
    };
    let borderColor = nebulaTheme === 'dark' ? '#1d1d1d' : '#f0f0f0';
    if (!!border) {
      style['border'] = `solid 1px ${borderColor}`;
    }
    return (
      <div 
        ref={this.assignRef} 
        style={style} 
        className="react-monaco-editor-container" 
      />
    );
  }
}

Editor.propTypes = {
  width: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  height: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  value: PropTypes.string,
  fontSize: PropTypes.number,
  defaultValue: PropTypes.string,
  language: PropTypes.string,
  theme: PropTypes.string,
  options: PropTypes.object,
  editorDidMount: PropTypes.func,
  editorWillMount: PropTypes.func,
  onChange: PropTypes.func,
  onFocus: PropTypes.func,
  onBlur: PropTypes.func,
};

// https://microsoft.github.io/monaco-editor/
Editor.defaultProps = {
  width: '100%',
  height: '90%',
  value: null,
  fontSize: 16,
  defaultValue: '',
  language: 'python',
  // theme: 'vs-dark', # vs-dark, hc-black, vs
  theme: 'myTheme',
  options: {},
  editorDidMount: noop,
  editorWillMount: noop,
  onChange: noop,
  onFocus: noop,
  onBlur: noop,
};

export default Editor;
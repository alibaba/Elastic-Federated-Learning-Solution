import { useState, useCallback } from 'react'

export default function useExpandedRowKeys() {
  const initialState = {
    train: [],
    sample: []
  };
  const [expandedRowKeys, setExpandedRowKeys] = useState(initialState);
  const expandItem = (namespace: string, keys: string[]) => {
    setExpandedRowKeys(r => {
      let newRowKeys = { ...r };
      newRowKeys[namespace] = keys;
      return newRowKeys
    })
  };
  const updateExpandedRowKeys = useCallback((namespace, record) => expandItem(namespace, record), []);
  return {
    expandedRowKeys,
    updateExpandedRowKeys,
  }
}
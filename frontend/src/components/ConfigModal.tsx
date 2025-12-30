import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { useWorkflowStore } from '../store/workflowStore';
import { BlockConfig, BlockType } from '../types/workflow';

export default function ConfigModal() {
  const {
    selectedNodeId,
    setSelectedNodeId,
    nodes,
    updateNodeConfig,
    blockTypes,
    files,
    fetchFiles,
  } = useWorkflowStore();

  const [localConfig, setLocalConfig] = useState<BlockConfig>({});

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);
  const blockType = selectedNode?.data.blockType as BlockType | undefined;
  const blockTypeInfo = blockTypes.find((b) => b.type === blockType);

  useEffect(() => {
    if (selectedNode) {
      setLocalConfig(selectedNode.data.config || {});
    }
  }, [selectedNode]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  if (!selectedNodeId || !selectedNode || !blockTypeInfo) {
    return null;
  }

  const handleSave = () => {
    updateNodeConfig(selectedNodeId, localConfig);
    setSelectedNodeId(null);
  };

  const handleClose = () => {
    setSelectedNodeId(null);
  };

  const updateLocalConfig = (key: string, value: unknown) => {
    setLocalConfig((prev) => ({ ...prev, [key]: value }));
  };

  const renderField = (key: string, schema: {
    type: string;
    required?: boolean;
    default?: unknown;
    enum?: string[];
    description?: string;
  }) => {
    const value = localConfig[key] ?? schema.default ?? '';

    // Special handling for file_path in read_csv
    if (key === 'file_path' && blockType === 'read_csv') {
      return (
        <select
          value={String(value)}
          onChange={(e) => updateLocalConfig(key, e.target.value)}
          className="w-full rounded-lg border border-[#2a2a3a] bg-[#1a1a24] px-3 py-2 text-sm text-white focus:border-block-purple focus:outline-none"
        >
          <option value="">Select a file...</option>
          {files.map((file) => (
            <option key={file} value={file}>
              {file}
            </option>
          ))}
        </select>
      );
    }

    // Enum field
    if (schema.enum) {
      return (
        <select
          value={String(value)}
          onChange={(e) => updateLocalConfig(key, e.target.value)}
          className="w-full rounded-lg border border-[#2a2a3a] bg-[#1a1a24] px-3 py-2 text-sm text-white focus:border-block-purple focus:outline-none"
        >
          {schema.enum.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      );
    }

    // Boolean field
    if (schema.type === 'boolean') {
      return (
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => updateLocalConfig(key, e.target.checked)}
            className="h-4 w-4 rounded border-[#2a2a3a] bg-[#1a1a24] text-block-purple focus:ring-block-purple"
          />
          <span className="text-sm text-white/70">Enabled</span>
        </label>
      );
    }

    // Array field (for struct in enrich_lead)
    if (schema.type === 'array' && key === 'struct') {
      const structValue = (value as Array<{name: string; description: string}>) || [];
      return (
        <div className="space-y-2">
          {structValue.map((item, idx) => (
            <div key={idx} className="flex gap-2">
              <input
                type="text"
                value={item.name || ''}
                onChange={(e) => {
                  const newStruct = [...structValue];
                  newStruct[idx] = { ...newStruct[idx], name: e.target.value };
                  updateLocalConfig(key, newStruct);
                }}
                placeholder="Field name"
                className="flex-1 rounded-lg border border-[#2a2a3a] bg-[#1a1a24] px-3 py-2 text-sm text-white focus:border-block-purple focus:outline-none"
              />
              <input
                type="text"
                value={item.description || ''}
                onChange={(e) => {
                  const newStruct = [...structValue];
                  newStruct[idx] = { ...newStruct[idx], description: e.target.value };
                  updateLocalConfig(key, newStruct);
                }}
                placeholder="Description"
                className="flex-1 rounded-lg border border-[#2a2a3a] bg-[#1a1a24] px-3 py-2 text-sm text-white focus:border-block-purple focus:outline-none"
              />
              <button
                onClick={() => {
                  const newStruct = structValue.filter((_, i) => i !== idx);
                  updateLocalConfig(key, newStruct);
                }}
                className="rounded-lg border border-red-500/30 px-2 text-red-400 hover:bg-red-500/10"
              >
                ×
              </button>
            </div>
          ))}
          <button
            onClick={() => {
              updateLocalConfig(key, [...structValue, { name: '', description: '' }]);
            }}
            className="text-sm text-block-purple hover:underline"
          >
            + Add field
          </button>
        </div>
      );
    }

    // Default text/string field
    return (
      <input
        type="text"
        value={String(value)}
        onChange={(e) => updateLocalConfig(key, e.target.value)}
        placeholder={schema.description || `Enter ${key}`}
        className="w-full rounded-lg border border-[#2a2a3a] bg-[#1a1a24] px-3 py-2 text-sm text-white focus:border-block-purple focus:outline-none"
      />
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl border border-[#2a2a3a] bg-[#12121a] shadow-2xl">
        {/* Header */}
        <div
          className="flex items-center justify-between rounded-t-xl px-4 py-3"
          style={{ backgroundColor: `${blockTypeInfo.color}20` }}
        >
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: blockTypeInfo.color }}
            />
            <h2 className="font-semibold text-white">{blockTypeInfo.name}</h2>
          </div>
          <button
            onClick={handleClose}
            className="rounded p-1 hover:bg-white/10"
          >
            <X size={18} className="text-white/70" />
          </button>
        </div>

        {/* Body */}
        <div className="max-h-[60vh] overflow-y-auto p-4">
          <div className="space-y-4">
            {Object.entries(blockTypeInfo.config_schema).map(([key, schema]) => (
              <div key={key}>
                <label className="mb-1 block text-sm font-medium text-white/70">
                  {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  {schema.required && <span className="text-red-400">*</span>}
                </label>
                {renderField(key, schema)}
                {schema.description && (
                  <p className="mt-1 text-xs text-white/40">{schema.description}</p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 border-t border-[#2a2a3a] p-4">
          <button
            onClick={handleClose}
            className="rounded-lg border border-[#2a2a3a] px-4 py-2 text-sm text-white/70 hover:bg-white/5"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="rounded-lg bg-block-purple px-4 py-2 text-sm font-medium text-white hover:bg-block-purple/90"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}


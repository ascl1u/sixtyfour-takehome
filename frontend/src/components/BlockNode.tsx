import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Settings, Trash2 } from 'lucide-react';
import { useWorkflowStore } from '../store/workflowStore';
import { BlockType } from '../types/workflow';

interface BlockNodeData {
  blockType: BlockType;
  label: string;
  color: string;
  config: Record<string, unknown>;
}

const BlockNode = memo(({ id, data, selected }: NodeProps) => {
  const nodeData = data as BlockNodeData;
  const { setSelectedNodeId, deleteNode, workflowStatus } = useWorkflowStore();
  
  // Find block progress if executing
  const blockProgress = workflowStatus?.blocks.find((b) => b.block_id === id);
  const isRunning = blockProgress?.status === 'running';
  const isCompleted = blockProgress?.status === 'completed';
  const isFailed = blockProgress?.status === 'failed';
  
  const getStatusBorder = () => {
    if (isRunning) return 'border-yellow-400 animate-pulse';
    if (isCompleted) return 'border-green-400';
    if (isFailed) return 'border-red-400';
    return selected ? 'border-white/30' : 'border-transparent';
  };

  return (
    <div
      className={`
        relative min-w-[200px] rounded-lg border-2 ${getStatusBorder()}
        bg-[#12121a] shadow-lg transition-all duration-200
        hover:shadow-xl
      `}
      style={{
        boxShadow: `0 4px 20px ${nodeData.color}20`,
      }}
    >
      {/* Header */}
      <div
        className="flex items-center gap-2 rounded-t-lg px-3 py-2"
        style={{ backgroundColor: `${nodeData.color}30` }}
      >
        <div
          className="h-3 w-3 rounded-sm"
          style={{ backgroundColor: nodeData.color }}
        />
        <span className="flex-1 text-sm font-medium text-white">
          {nodeData.label}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            setSelectedNodeId(id);
          }}
          className="rounded p-1 hover:bg-white/10"
          title="Configure"
        >
          <Settings size={14} className="text-white/70" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            deleteNode(id);
          }}
          className="rounded p-1 hover:bg-red-500/20"
          title="Delete"
        >
          <Trash2 size={14} className="text-white/70" />
        </button>
      </div>

      {/* Body - show config summary */}
      <div className="px-3 py-2 text-xs text-white/60">
        {Object.entries(nodeData.config).length > 0 ? (
          <div className="space-y-1">
            {Object.entries(nodeData.config).slice(0, 2).map(([key, value]) => (
              <div key={key} className="truncate">
                <span className="text-white/40">{key}:</span>{' '}
                <span className="text-white/80">
                  {String(value).substring(0, 20)}
                  {String(value).length > 20 ? '...' : ''}
                </span>
              </div>
            ))}
            {Object.entries(nodeData.config).length > 2 && (
              <div className="text-white/40">
                +{Object.entries(nodeData.config).length - 2} more
              </div>
            )}
          </div>
        ) : (
          <span className="italic">Click to configure</span>
        )}
      </div>

      {/* Progress bar */}
      {isRunning && blockProgress && (
        <div className="absolute bottom-0 left-0 right-0 h-1 overflow-hidden rounded-b-lg bg-white/10">
          <div
            className="h-full bg-yellow-400 transition-all duration-300"
            style={{ width: `${blockProgress.progress}%` }}
          />
        </div>
      )}

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-[#2a2a3a] !border-[#3a3a4a]"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-[#2a2a3a] !border-[#3a3a4a]"
      />
    </div>
  );
});

BlockNode.displayName = 'BlockNode';

export default BlockNode;


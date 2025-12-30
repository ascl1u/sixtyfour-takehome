import { useEffect } from 'react';
import {
  FileSpreadsheet,
  Search,
  Filter,
  UserPlus,
  Mail,
  Save,
  Play,
  RotateCcw,
  Loader2,
} from 'lucide-react';
import { useWorkflowStore } from '../store/workflowStore';
import { BlockType } from '../types/workflow';

const blockIcons: Record<BlockType, React.ReactNode> = {
  read_csv: <FileSpreadsheet size={18} />,
  enrich_lead: <UserPlus size={18} />,
  find_email: <Mail size={18} />,
  filter: <Filter size={18} />,
  save_csv: <Save size={18} />,
};

export default function Sidebar() {
  const {
    blockTypes,
    fetchBlockTypes,
    addNode,
    executeWorkflow,
    resetExecution,
    isExecuting,
    workflowStatus,
  } = useWorkflowStore();

  useEffect(() => {
    fetchBlockTypes();
  }, [fetchBlockTypes]);

  const onDragStart = (
    event: React.DragEvent<HTMLDivElement>,
    blockType: BlockType
  ) => {
    event.dataTransfer.setData('application/reactflow', blockType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="flex h-full w-64 flex-col border-r border-[#2a2a3a] bg-[#12121a]">
      {/* Header */}
      <div className="border-b border-[#2a2a3a] px-4 py-4">
        <h1 className="text-lg font-bold text-white">
          <span className="text-block-purple">64</span> Workflow
        </h1>
        <p className="mt-1 text-xs text-white/50">
          Drag blocks to build your workflow
        </p>
      </div>

      {/* Blocks */}
      <div className="flex-1 overflow-y-auto p-4">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-white/40">
          Blocks
        </h2>
        <div className="space-y-2">
          {blockTypes.map((block) => (
            <div
              key={block.type}
              className="cursor-grab rounded-lg border border-[#2a2a3a] bg-[#1a1a24] p-3 transition-all hover:border-[#3a3a4a] hover:bg-[#22222e] active:cursor-grabbing"
              draggable
              onDragStart={(e) => onDragStart(e, block.type as BlockType)}
              onClick={() => {
                // Also allow click to add at a default position
                addNode(block.type as BlockType, { x: 300, y: 200 });
              }}
              style={{
                borderLeftWidth: '3px',
                borderLeftColor: block.color,
              }}
            >
              <div className="flex items-center gap-2">
                <span style={{ color: block.color }}>
                  {blockIcons[block.type as BlockType]}
                </span>
                <span className="text-sm font-medium text-white">
                  {block.name}
                </span>
              </div>
              <p className="mt-1 text-xs text-white/50">{block.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Status */}
      {workflowStatus && (
        <div className="border-t border-[#2a2a3a] p-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-white/40">
            Status
          </h3>
          <div
            className={`text-sm font-medium ${
              workflowStatus.status === 'completed'
                ? 'text-green-400'
                : workflowStatus.status === 'failed'
                ? 'text-red-400'
                : workflowStatus.status === 'running'
                ? 'text-yellow-400'
                : 'text-white/60'
            }`}
          >
            {workflowStatus.status.toUpperCase()}
          </div>
          {workflowStatus.result_row_count > 0 && (
            <div className="mt-1 text-xs text-white/50">
              {workflowStatus.result_row_count} rows processed
            </div>
          )}
          {workflowStatus.error && (
            <div className="mt-2 text-xs text-red-400">
              {workflowStatus.error}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="border-t border-[#2a2a3a] p-4">
        <button
          onClick={executeWorkflow}
          disabled={isExecuting}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-block-purple px-4 py-2.5 font-medium text-white transition-all hover:bg-block-purple/90 disabled:opacity-50"
        >
          {isExecuting ? (
            <>
              <Loader2 size={18} className="animate-spin" />
              Running...
            </>
          ) : (
            <>
              <Play size={18} />
              Run Workflow
            </>
          )}
        </button>
        {workflowStatus && (
          <button
            onClick={resetExecution}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg border border-[#2a2a3a] px-4 py-2 text-sm text-white/70 transition-all hover:bg-white/5"
          >
            <RotateCcw size={16} />
            Reset
          </button>
        )}
      </div>
    </div>
  );
}


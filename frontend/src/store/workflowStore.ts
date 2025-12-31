import { create } from 'zustand';
import {
  Node,
  Edge,
  Connection,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  NodeChange,
  EdgeChange,
} from '@xyflow/react';
import { BlockType, BlockConfig, BlockTypeInfo, WorkflowStatusResponse, WorkflowResult } from '../types/workflow';

const API_BASE = '/api';

interface WorkflowStore {
  // Node/Edge state
  nodes: Node[];
  edges: Edge[];
  
  // Block types from API
  blockTypes: BlockTypeInfo[];
  
  // Execution state
  workflowId: string | null;
  workflowStatus: WorkflowStatusResponse | null;
  workflowResult: WorkflowResult | null;
  isExecuting: boolean;
  isPaused: boolean;
  
  // Selected node for configuration
  selectedNodeId: string | null;
  
  // Available files
  files: string[];
  
  // Actions
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  
  addNode: (type: BlockType, position: { x: number; y: number }) => void;
  deleteNode: (nodeId: string) => void;
  updateNodeConfig: (nodeId: string, config: BlockConfig) => void;
  
  setSelectedNodeId: (nodeId: string | null) => void;
  
  fetchBlockTypes: () => Promise<void>;
  fetchFiles: () => Promise<void>;
  
  executeWorkflow: () => Promise<void>;
  pauseWorkflow: () => Promise<void>;
  resumeWorkflow: () => Promise<void>;
  pollWorkflowStatus: () => Promise<void>;
  fetchWorkflowResult: () => Promise<void>;
  resetExecution: () => void;
}

let nodeIdCounter = 0;

export const useWorkflowStore = create<WorkflowStore>((set, get) => ({
  nodes: [],
  edges: [],
  blockTypes: [],
  workflowId: null,
  workflowStatus: null,
  workflowResult: null,
  isExecuting: false,
  isPaused: false,
  selectedNodeId: null,
  files: [],

  onNodesChange: (changes) => {
    set({ nodes: applyNodeChanges(changes, get().nodes) });
  },

  onEdgesChange: (changes) => {
    set({ edges: applyEdgeChanges(changes, get().edges) });
  },

  onConnect: (connection) => {
    set({ edges: addEdge({ ...connection, animated: true }, get().edges) });
  },

  addNode: (type, position) => {
    const id = `node-${++nodeIdCounter}`;
    const blockType = get().blockTypes.find((b) => b.type === type);
    
    // Build default config from schema
    const defaultConfig: BlockConfig = {};
    if (blockType?.config_schema) {
      Object.entries(blockType.config_schema).forEach(([key, schema]) => {
        if (schema.default !== undefined) {
          defaultConfig[key] = schema.default;
        }
      });
    }
    
    const newNode: Node = {
      id,
      type: 'blockNode',
      position,
      data: {
        blockType: type,
        label: blockType?.name || type,
        color: blockType?.color || '#6B7280',
        config: defaultConfig,
      },
    };
    
    set({ nodes: [...get().nodes, newNode] });
  },

  deleteNode: (nodeId) => {
    set({
      nodes: get().nodes.filter((n) => n.id !== nodeId),
      edges: get().edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
      selectedNodeId: get().selectedNodeId === nodeId ? null : get().selectedNodeId,
    });
  },

  updateNodeConfig: (nodeId, config) => {
    set({
      nodes: get().nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, config: { ...node.data.config, ...config } } }
          : node
      ),
    });
  },

  setSelectedNodeId: (nodeId) => {
    set({ selectedNodeId: nodeId });
  },

  fetchBlockTypes: async () => {
    try {
      const response = await fetch(`${API_BASE}/blocks`);
      const data = await response.json();
      set({ blockTypes: data.blocks });
    } catch (error) {
      console.error('Failed to fetch block types:', error);
    }
  },

  fetchFiles: async () => {
    try {
      const response = await fetch(`${API_BASE}/files`);
      const data = await response.json();
      set({ files: data.files });
    } catch (error) {
      console.error('Failed to fetch files:', error);
    }
  },

  executeWorkflow: async () => {
    const { nodes, edges } = get();
    
    if (nodes.length === 0) {
      alert('Please add at least one block to the workflow');
      return;
    }

    // Build ordered list of blocks based on edges
    const orderedBlocks = getOrderedBlocks(nodes, edges);
    
    if (orderedBlocks.length === 0) {
      alert('Please connect your blocks to form a workflow');
      return;
    }

    set({ isExecuting: true, workflowStatus: null, workflowResult: null });

    try {
      const response = await fetch(`${API_BASE}/workflows/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          blocks: orderedBlocks.map((node) => ({
            id: node.id,
            type: node.data.blockType,
            config: node.data.config,
          })),
        }),
      });

      const data = await response.json();
      set({ workflowId: data.workflow_id });

      // Start polling
      get().pollWorkflowStatus();
    } catch (error) {
      console.error('Failed to execute workflow:', error);
      set({ isExecuting: false });
    }
  },

  pollWorkflowStatus: async () => {
    const { workflowId } = get();
    if (!workflowId) return;

    try {
      const response = await fetch(`${API_BASE}/workflows/${workflowId}/status`);
      const status: WorkflowStatusResponse = await response.json();
      set({ workflowStatus: status });

      if (status.status === 'running' || status.status === 'pending') {
        // Continue polling
        setTimeout(() => get().pollWorkflowStatus(), 1000);
      } else if (status.status === 'completed') {
        set({ isExecuting: false, isPaused: false });
        get().fetchWorkflowResult();
      } else if (status.status === 'paused') {
        set({ isExecuting: false, isPaused: true });
        get().fetchWorkflowResult();
      } else {
        set({ isExecuting: false, isPaused: false });
      }
    } catch (error) {
      console.error('Failed to poll workflow status:', error);
      set({ isExecuting: false, isPaused: false });
    }
  },

  fetchWorkflowResult: async () => {
    const { workflowId } = get();
    if (!workflowId) return;

    try {
      const response = await fetch(`${API_BASE}/workflows/${workflowId}/results`);
      const result: WorkflowResult = await response.json();
      set({ workflowResult: result });
    } catch (error) {
      console.error('Failed to fetch workflow result:', error);
    }
  },

  pauseWorkflow: async () => {
    const { workflowId } = get();
    if (!workflowId) return;

    try {
      const response = await fetch(`${API_BASE}/workflows/${workflowId}/pause`, {
        method: 'POST',
      });
      
      if (response.ok) {
        // Continue polling - status will change to 'paused'
      } else {
        console.error('Failed to pause workflow');
      }
    } catch (error) {
      console.error('Failed to pause workflow:', error);
    }
  },

  resumeWorkflow: async () => {
    const { workflowId } = get();
    if (!workflowId) return;

    try {
      const response = await fetch(`${API_BASE}/workflows/${workflowId}/resume`, {
        method: 'POST',
      });
      
      if (response.ok) {
        set({ isExecuting: true, isPaused: false });
        // Start polling again
        get().pollWorkflowStatus();
      } else {
        console.error('Failed to resume workflow');
      }
    } catch (error) {
      console.error('Failed to resume workflow:', error);
    }
  },

  resetExecution: () => {
    set({
      workflowId: null,
      workflowStatus: null,
      workflowResult: null,
      isExecuting: false,
      isPaused: false,
    });
  },
}));

// Helper to order blocks based on graph topology
function getOrderedBlocks(nodes: Node[], edges: Edge[]): Node[] {
  if (nodes.length === 0) return [];
  if (edges.length === 0) return nodes;

  // Build adjacency list
  const graph = new Map<string, string[]>();
  const inDegree = new Map<string, number>();
  
  nodes.forEach((node) => {
    graph.set(node.id, []);
    inDegree.set(node.id, 0);
  });

  edges.forEach((edge) => {
    graph.get(edge.source)?.push(edge.target);
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
  });

  // Topological sort (Kahn's algorithm)
  const queue: string[] = [];
  const result: Node[] = [];

  inDegree.forEach((degree, nodeId) => {
    if (degree === 0) queue.push(nodeId);
  });

  while (queue.length > 0) {
    const current = queue.shift()!;
    const node = nodes.find((n) => n.id === current);
    if (node) result.push(node);

    graph.get(current)?.forEach((neighbor) => {
      const newDegree = (inDegree.get(neighbor) || 1) - 1;
      inDegree.set(neighbor, newDegree);
      if (newDegree === 0) queue.push(neighbor);
    });
  }

  return result;
}


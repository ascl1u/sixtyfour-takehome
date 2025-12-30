export type BlockType = 
  | 'read_csv'
  | 'save_csv'
  | 'filter'
  | 'enrich_lead'
  | 'find_email';

export interface BlockConfig {
  [key: string]: unknown;
}

export interface BlockDefinition {
  id: string;
  type: BlockType;
  config: BlockConfig;
}

export interface BlockTypeInfo {
  type: BlockType;
  name: string;
  description: string;
  color: string;
  config_schema: Record<string, {
    type: string;
    required?: boolean;
    default?: unknown;
    enum?: string[];
    description?: string;
  }>;
}

export type BlockStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

export interface BlockProgress {
  block_id: string;
  block_type: string;
  status: BlockStatus;
  progress: number;
  error?: string;
}

export type WorkflowStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface WorkflowStatusResponse {
  workflow_id: string;
  status: WorkflowStatus;
  blocks: BlockProgress[];
  current_block_index: number;
  error?: string;
  result_preview?: Record<string, unknown>[];
  result_columns?: string[];
  result_row_count: number;
}

export interface WorkflowResult {
  columns: string[];
  row_count: number;
  data: Record<string, unknown>[];
}

export interface FileInfo {
  name: string;
  columns?: string[];
}


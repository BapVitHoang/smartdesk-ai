export interface KnowledgeArticle {
  doc_id: string;
  category: string;
  title: string;
  content: string;
  source_url: string;
}

export interface DocumentItem {
  id: number;
  workspace_id: number;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'verified' | 'published' | 'failed';
  chunk_count: number;
  created_at: string;
  updated_at?: string;
}

export interface DocumentChunk {
  id: number;
  chunk_id: string;
  chunk_index: number;
  page_number: number;
  title: string;
  content: string;
}

export interface VerificationItem {
  id: number;
  question: string;
  ground_truth: string;
  rag_answer: string;
  score: number;
  status: 'passed' | 'warning' | 'failed';
  reason?: string;
}

export interface AgentTraceStep {
  agent: string;
  action: string;
  input_summary?: string;
  output_summary?: string;
  latency_ms?: number;
  status: 'success' | 'failed' | 'skipped';
  timestamp?: string;
}

export interface VerificationReport {
  id: number;
  document_id: number;
  workspace_id: number;
  faithfulness_score: number;
  status: 'passed' | 'warning' | 'failed';
  created_at: string;
  items: VerificationItem[];
  agent_trace?: AgentTraceStep[];
}

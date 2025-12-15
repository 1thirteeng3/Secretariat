export type IntentType = 'QUICK_NOTE' | 'TASK' | 'CALENDAR_EVENT' | 'JOURNAL_ENTRY';

export interface InboxItem {
  id: string; // UUID
  source_device_id: string;
  created_at: string; // ISO String
  content_type: 'AUDIO' | 'TEXT';
  content_url?: string; // URL do áudio no Storage bucket (se audio)
  raw_text?: string;
  // O texto digitado (se texto)
  status: 'PENDING' | 'PROCESSING' | 'WAITING_APPROVAL' | 'DONE';
}

export interface AIStructuredResult {
  title: string;
  summary: string;
  formatted_markdown: string;
  detected_intent: IntentType;
  // Metadata gerado pela IA
  tags: string[];
  suggested_backlinks: string[]; // Títulos de outras notas
  // Se for uma tarefa ou evento
  action_item?: {
    due_date?: string;
    priority: 'HIGH' | 'MEDIUM' | 'LOW';
    is_event: boolean; // Se true, vai pra agenda
  }
}

export interface GraphNode {
  id: string; // Caminho do arquivo ou UUID
  name: string; // Título da nota
  val: number; // Peso (baseado no número de conexões)
  group?: string; // Baseado em Tags principais
}

export interface GraphLink {
  source: string; // ID do nó origem
  target: string; // ID do nó destino
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

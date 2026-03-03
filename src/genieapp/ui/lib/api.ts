/**
 * GenieApp API client — manually written to match FastAPI backend.
 */

import axios from "axios";
import {
  useQuery,
  useMutation,
  type UseQueryOptions,
} from "@tanstack/react-query";

const api = axios.create({ baseURL: "/api" });

// --- Types ---

export interface BrandingOut {
  company_name: string;
  description: string;
  logo_path: string;
  primary_color: string;
  secondary_color: string;
}

export interface AppConfigOut {
  space_id: string;
  display_name: string;
  sample_questions: string[];
  branding: BrandingOut;
}

export interface ChartSuggestion {
  chart_type: "bar" | "line" | "pie" | "area" | "kpi" | "table";
  x_axis: string | null;
  y_axis: string | null;
  title: string;
}

export interface ChatMessageOut {
  conversation_id: string;
  message_id: string;
  status: string;
  description: string;
  sql: string;
  columns: string[];
  data: Record<string, string | number | null>[];
  row_count: number;
  chart_suggestion: ChartSuggestion | null;
  error: string | null;
  suggested_questions: string[];
  query_description: string;
  is_truncated: boolean;
  is_clarification: boolean;
  error_type: string;
}

export interface ChatStartOut {
  conversation_id: string;
  message_id: string;
}

export interface ChatStatusOut {
  status: string;
  is_complete: boolean;
}

export interface FeedbackIn {
  conversation_id: string;
  message_id: string;
  rating: "POSITIVE" | "NEGATIVE";
}

export interface TableInfoOut {
  full_name: string;
  table_name: string;
  comment: string;
}

export interface ColumnInfo {
  name: string;
  type: string;
  comment: string;
}

export interface TableDetailOut {
  full_name: string;
  table_name: string;
  comment: string;
  columns: ColumnInfo[];
  row_count: number;
}

export interface ConversationOut {
  conversation_id: string;
  first_question: string;
  message_count: number;
}

// --- API Functions ---

export async function getAppConfig(): Promise<AppConfigOut> {
  const { data } = await api.get<AppConfigOut>("/config");
  return data;
}

export async function sendChatMessage(
  question: string,
  conversationId?: string,
): Promise<ChatMessageOut> {
  const { data } = await api.post<ChatMessageOut>("/chat", {
    question,
    conversation_id: conversationId || null,
  });
  return data;
}

export async function startChat(
  question: string,
  conversationId?: string,
): Promise<ChatStartOut> {
  const { data } = await api.post<ChatStartOut>("/chat/start", {
    question,
    conversation_id: conversationId || null,
  });
  return data;
}

export async function getChatStatus(
  conversationId: string,
  messageId: string,
): Promise<ChatStatusOut> {
  const { data } = await api.get<ChatStatusOut>(
    `/chat/${conversationId}/${messageId}/status`,
  );
  return data;
}

export async function getChatResult(
  conversationId: string,
  messageId: string,
): Promise<ChatMessageOut> {
  const { data } = await api.get<ChatMessageOut>(
    `/chat/${conversationId}/${messageId}/result`,
  );
  return data;
}

export async function sendFeedback(feedback: FeedbackIn): Promise<void> {
  await api.post("/chat/feedback", feedback);
}

export async function listTables(): Promise<TableInfoOut[]> {
  const { data } = await api.get<TableInfoOut[]>("/tables");
  return data;
}

export async function getTableDetail(
  name: string,
): Promise<TableDetailOut> {
  const { data } = await api.get<TableDetailOut>(`/tables/${name}`);
  return data;
}

export async function listConversations(): Promise<ConversationOut[]> {
  const { data } = await api.get<ConversationOut[]>("/conversations");
  return data;
}

export async function exportConversation(
  conversationId: string,
  format: "json" | "csv" = "csv",
): Promise<Blob> {
  const { data } = await api.post(
    "/export",
    { conversation_id: conversationId, format },
    { responseType: "blob" },
  );
  return data;
}

// --- React Query Hooks ---

export function useAppConfig(
  options?: Partial<UseQueryOptions<AppConfigOut>>,
) {
  return useQuery({
    queryKey: ["appConfig"],
    queryFn: getAppConfig,
    staleTime: Infinity,
    ...options,
  });
}

export function useTables(
  options?: Partial<UseQueryOptions<TableInfoOut[]>>,
) {
  return useQuery({
    queryKey: ["tables"],
    queryFn: listTables,
    staleTime: 60_000,
    ...options,
  });
}

export function useTableDetail(
  name: string,
  options?: Partial<UseQueryOptions<TableDetailOut>>,
) {
  return useQuery({
    queryKey: ["tableDetail", name],
    queryFn: () => getTableDetail(name),
    enabled: !!name,
    ...options,
  });
}

export function useConversations(
  options?: Partial<UseQueryOptions<ConversationOut[]>>,
) {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
    staleTime: 10_000,
    ...options,
  });
}

export function useSendMessage() {
  return useMutation({
    mutationFn: ({
      question,
      conversationId,
    }: {
      question: string;
      conversationId?: string;
    }) => sendChatMessage(question, conversationId),
  });
}

export function useStartChat() {
  return useMutation({
    mutationFn: ({
      question,
      conversationId,
    }: {
      question: string;
      conversationId?: string;
    }) => startChat(question, conversationId),
  });
}

export function useChatStatus(
  conversationId: string | null,
  messageId: string | null,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ["chatStatus", conversationId, messageId],
    queryFn: () => getChatStatus(conversationId!, messageId!),
    enabled: enabled && !!conversationId && !!messageId,
    refetchInterval: enabled ? 1000 : false,
  });
}

export function useChatResult(
  conversationId: string | null,
  messageId: string | null,
  enabled: boolean,
) {
  return useQuery({
    queryKey: ["chatResult", conversationId, messageId],
    queryFn: () => getChatResult(conversationId!, messageId!),
    enabled: enabled && !!conversationId && !!messageId,
  });
}

export function useSendFeedback() {
  return useMutation({
    mutationFn: (feedback: FeedbackIn) => sendFeedback(feedback),
  });
}

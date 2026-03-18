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
  accent_color: string;
  chart_colors: string[];
}

export interface TableInfoBrief {
  full_name: string;
  table_name: string;
  comment: string;
}

export interface AppConfigOut {
  space_id: string;
  display_name: string;
  sample_questions: string[];
  branding: BrandingOut;
  tables: TableInfoBrief[];
}

export interface ChartSuggestion {
  chart_type: "bar" | "line" | "pie" | "area" | "kpi" | "map" | "table";
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

export interface ConversationMessageOut {
  question: string;
  response: ChatMessageOut | null;
}

export interface SpaceOut {
  space_id: string;
  company_name: string;
  description: string;
  logo_path: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  chart_colors: string[];
  template_id: string;
  space_type: string;
  created_at: string;
}

export interface UserOut {
  user_id: string;
  email: string;
  username: string;
  default_template: string;
  preferences: Record<string, unknown>;
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
  spaceId?: string,
): Promise<ChatStartOut> {
  const { data } = await api.post<ChatStartOut>("/chat/start", {
    question,
    conversation_id: conversationId || null,
    space_id: spaceId || null,
  });
  return data;
}

export async function getChatStatus(
  conversationId: string,
  messageId: string,
  spaceId?: string,
): Promise<ChatStatusOut> {
  const { data } = await api.get<ChatStatusOut>(
    `/chat/${conversationId}/${messageId}/status`,
    { params: spaceId ? { space_id: spaceId } : {} },
  );
  return data;
}

export async function getChatResult(
  conversationId: string,
  messageId: string,
  spaceId?: string,
): Promise<ChatMessageOut> {
  const { data } = await api.get<ChatMessageOut>(
    `/chat/${conversationId}/${messageId}/result`,
    { params: spaceId ? { space_id: spaceId } : {} },
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

export async function listConversations(spaceId?: string): Promise<ConversationOut[]> {
  const { data } = await api.get<ConversationOut[]>("/conversations", {
    params: spaceId ? { space_id: spaceId } : {},
  });
  return data;
}

export async function getConversationMessages(
  conversationId: string,
): Promise<ConversationMessageOut[]> {
  const { data } = await api.get<ConversationMessageOut[]>(
    `/conversations/${conversationId}`,
  );
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
  spaceId?: string,
  options?: Partial<UseQueryOptions<ConversationOut[]>>,
) {
  return useQuery({
    queryKey: ["conversations", spaceId],
    queryFn: () => listConversations(spaceId),
    staleTime: 10_000,
    ...options,
  });
}

export function useConversationMessages(
  conversationId: string | undefined,
) {
  return useQuery({
    queryKey: ["conversationMessages", conversationId],
    queryFn: () => getConversationMessages(conversationId!),
    enabled: !!conversationId,
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
      spaceId,
    }: {
      question: string;
      conversationId?: string;
      spaceId?: string;
    }) => startChat(question, conversationId, spaceId),
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

// --- Spaces ---

export async function listSpaces(): Promise<SpaceOut[]> {
  const { data } = await api.get<SpaceOut[]>("/spaces");
  return data;
}

export function useSpaces(
  options?: Partial<UseQueryOptions<SpaceOut[]>>,
) {
  return useQuery({
    queryKey: ["spaces"],
    queryFn: listSpaces,
    staleTime: 30_000,
    ...options,
  });
}

// --- Space creation & jobs ---

export interface CreateSpaceOut {
  run_id: string;
}

export interface JobStatusOut {
  run_id: string;
  status: "RUNNING" | "COMPLETED" | "FAILED";
  space_id: string | null;
  error: string | null;
}

export async function createSpace(
  companyName: string,
  description: string,
  logoUrl?: string,
): Promise<CreateSpaceOut> {
  const { data } = await api.post<CreateSpaceOut>("/spaces", {
    company_name: companyName,
    description,
    logo_url: logoUrl || "",
  });
  return data;
}

export async function getJobStatus(runId: string): Promise<JobStatusOut> {
  const { data } = await api.get<JobStatusOut>(`/jobs/${runId}`);
  return data;
}

export async function getSpaceConfig(
  spaceId: string,
): Promise<AppConfigOut> {
  const { data } = await api.get<AppConfigOut>(`/spaces/${spaceId}/config`);
  return data;
}

export function useSpaceConfig(spaceId: string | undefined) {
  return useQuery({
    queryKey: ["spaceConfig", spaceId],
    queryFn: () => getSpaceConfig(spaceId!),
    enabled: !!spaceId,
    staleTime: Infinity,
  });
}

// --- Users ---

export async function getCurrentUser(): Promise<UserOut> {
  const { data } = await api.get<UserOut>("/users/me");
  return data;
}

export async function updateUserPreferences(prefs: {
  default_template?: string;
  preferences?: Record<string, unknown>;
}): Promise<UserOut> {
  const { data } = await api.patch<UserOut>("/users/me/preferences", prefs);
  return data;
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ["currentUser"],
    queryFn: getCurrentUser,
    staleTime: 300_000, // 5 min
  });
}

export function useUpdateUserPreferences() {
  return useMutation({
    mutationFn: updateUserPreferences,
  });
}

// --- Space template ---

export async function updateSpaceTemplate(
  spaceId: string,
  templateId: string,
): Promise<void> {
  await api.patch(`/spaces/${spaceId}/template`, { template_id: templateId });
}

export function useUpdateSpaceTemplate() {
  return useMutation({
    mutationFn: ({ spaceId, templateId }: { spaceId: string; templateId: string }) =>
      updateSpaceTemplate(spaceId, templateId),
  });
}

// --- BYOG ---

export async function createByogSpace(params: {
  space_id: string;
  company_name: string;
  primary_color?: string;
  secondary_color?: string;
  template_id?: string;
}): Promise<SpaceOut> {
  const { data } = await api.post<SpaceOut>("/spaces/byog", params);
  return data;
}

export function useCreateByogSpace() {
  return useMutation({
    mutationFn: createByogSpace,
  });
}

// --- Image upload ---

export async function uploadImage(
  file: File,
  spaceId?: string,
): Promise<{ image_id: string; volume_path: string }> {
  const formData = new FormData();
  formData.append("file", file);
  if (spaceId) formData.append("space_id", spaceId);
  const { data } = await api.post("/images/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export function getImageUrl(imageId: string): string {
  return `/api/images/${imageId}`;
}

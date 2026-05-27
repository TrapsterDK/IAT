export enum ResponseSide {
  Left,
  Right,
}

export enum SessionStateKind {
  Review,
  BlockIntro,
  Trial,
  Results,
}

export enum TrialResponseKind {
  Accepted,
  Ignored,
  Incorrect,
}

export enum TrialAdvanceKind {
  AdvancedBlock,
  AdvancedResult,
  AdvancedTrial,
  Ignored,
}

export interface CatalogItem {
  description: string;
  slug: string;
  title: string;
}

export interface IatStimulus {
  image_url: string | null;
  text: string | null;
}

export interface IatCategory {
  label: string;
  slug: string;
  stimuli: IatStimulus[];
}

export interface IatCategoryGroup {
  category: IatCategory[];
}

export interface IatDetail {
  categories: IatCategoryGroup[];
  description: string;
  slug: string;
  title: string;
}

export interface ClientContext {
  devicePixelRatio: number | null;
  platform: string | null;
  userAgent: string | null;
  viewportHeightPx: number | null;
  viewportWidthPx: number | null;
}

export type SessionMode = "evaluation" | "participant";

export interface SessionBootstrapTrial {
  correct_response_side: ResponseSide;
  stimulus: IatStimulus;
}

export interface SessionBootstrapBlock {
  is_practice: boolean;
  left_labels: string[];
  right_labels: string[];
  trials: SessionBootstrapTrial[];
}

export interface SessionBootstrap {
  blocks: SessionBootstrapBlock[];
  session_key: string;
}

export type SessionBlock = SessionBootstrap["blocks"][number];

export type SessionTrial = SessionBlock["trials"][number];

export interface SessionScore {
  d_score: number;
  headline: string;
}

export interface TrialEvent {
  elapsedMs: number;
  eventType: ResponseSide;
}

export interface CompletedTrial {
  events: TrialEvent[];
}

export interface CompletedBlockPayload {
  trials: CompletedTrial[];
}

export interface CatalogState {
  error: string | null;
  items: CatalogItem[];
  loading: boolean;
  startingIatSlug: string | null;
}

interface AssetState {
  imageObjectUrls: Map<string, string>;
}

interface DeviceState {
  prefersTouchInput: boolean;
}

interface UiState {
  screenError: string | null;
}

export interface PendingBlockUpload {
  blockIndex: number;
  payload: CompletedBlockPayload;
}

export interface SessionBlockUploadState {
  pendingUpload: PendingBlockUpload | null;
  uploadError: string | null;
  uploading: boolean;
}

export interface SessionPreloadState {
  failures: string[];
  inFlightCount: number;
  lastProgressAt: Date;
  loaded: number;
  running: boolean;
  startedAt: Date;
  total: number;
}

export interface ActiveTrialState {
  activeEvents: TrialEvent[];
  responseLocked: boolean;
  startedAtMs: number | null;
}

export interface SessionResultState {
  score: SessionScore | null;
  scoreError: string | null;
}

interface SessionBaseState {
  bootstrap: SessionBootstrap;
  iatDetail: IatDetail;
}

export interface SessionBlockProgressState extends SessionBaseState {
  currentBlockIndex: number;
}

interface SessionBlockUploadOwnerState {
  blockUpload: SessionBlockUploadState;
}

export interface SessionTrialProgressState extends SessionBlockProgressState {
  currentBlockTrials: CompletedTrial[];
  currentTrialIndex: number;
}

export interface ReviewSessionState extends SessionBaseState {
  preload: SessionPreloadState;
  state: SessionStateKind.Review;
}

export interface BlockIntroSessionState extends SessionBlockProgressState, SessionBlockUploadOwnerState {
  starting: boolean;
  state: SessionStateKind.BlockIntro;
}

export interface TrialSessionState extends SessionTrialProgressState {
  state: SessionStateKind.Trial;
  trial: ActiveTrialState;
}

export interface PendingResultSessionState extends SessionBaseState, SessionBlockUploadOwnerState {
  pending: true;
  result: SessionResultState;
  state: SessionStateKind.Results;
}

export interface CompletedResultSessionState extends SessionBaseState {
  pending: false;
  result: SessionResultState;
  state: SessionStateKind.Results;
}

export type ResultSessionState = PendingResultSessionState | CompletedResultSessionState;

export type SessionState = ReviewSessionState | BlockIntroSessionState | TrialSessionState | ResultSessionState;

export interface RuntimeState {
  assets: AssetState;
  catalog: CatalogState;
  device: DeviceState;
  session: SessionState | null;
  ui: UiState;
}

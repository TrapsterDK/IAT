export enum ResponseSide {
  Left,
  Right,
}

export enum SessionStateKind {
  Review,
  Preloading,
  BlockIntro,
  StartingBlock,
  Trial,
  Finalizing,
  Results,
}

export enum TrialResponseKind {
  Accepted,
  Ignored,
  Incorrect,
}

export enum TrialAdvanceKind {
  AdvancedBlock,
  AdvancedTrial,
  Finalizing,
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

export interface QueuedBlockUpload {
  blockIndex: number;
  lastError: string | null;
  payload: CompletedBlockPayload;
  uploaded: boolean;
}

export interface SessionBlockUploadsState {
  queuedBlockUploads: QueuedBlockUpload[];
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
  startedAtMs: number;
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
  blockUploads: SessionBlockUploadsState;
}

export interface SessionTrialProgressState extends SessionBlockProgressState {
  currentBlockTrials: CompletedTrial[];
  currentTrialIndex: number;
}

export interface ReviewSessionState extends SessionBaseState {
  state: SessionStateKind.Review;
}

export interface PreloadingSessionState extends SessionBaseState {
  preload: SessionPreloadState;
  state: SessionStateKind.Preloading;
}

export interface BlockIntroSessionState extends SessionBlockProgressState, SessionBlockUploadOwnerState {
  state: SessionStateKind.BlockIntro;
}

export interface StartingBlockSessionState extends SessionBlockProgressState, SessionBlockUploadOwnerState {
  state: SessionStateKind.StartingBlock;
}

export interface TrialSessionState extends SessionTrialProgressState, SessionBlockUploadOwnerState {
  state: SessionStateKind.Trial;
  trial: ActiveTrialState;
}

export interface FinalizingSessionState extends SessionBaseState, SessionBlockUploadOwnerState {
  pendingScoreError: string | null;
  state: SessionStateKind.Finalizing;
}

export interface ResultSessionState extends SessionBaseState {
  result: SessionResultState;
  state: SessionStateKind.Results;
}

export type SessionState =
  | ReviewSessionState
  | PreloadingSessionState
  | BlockIntroSessionState
  | StartingBlockSessionState
  | TrialSessionState
  | FinalizingSessionState
  | ResultSessionState;

export interface RuntimeState {
  assets: AssetState;
  catalog: CatalogState;
  device: DeviceState;
  session: SessionState | null;
  ui: UiState;
}

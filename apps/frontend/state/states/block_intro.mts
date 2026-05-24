import { SessionStateKind, type BlockIntroSessionState, type StartingBlockSessionState } from "../types.mjs";

export function beginStartingBlock(session: BlockIntroSessionState): StartingBlockSessionState {
  return {
    ...session,
    state: SessionStateKind.StartingBlock,
  };
}

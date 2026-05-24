import type { SessionBlockProgressState, SessionBootstrap, SessionTrialProgressState } from "./types.mjs";

export function currentBlock(session: SessionBlockProgressState) {
  return session.bootstrap.blocks[session.currentBlockIndex] ?? null;
}

export function currentTrial(session: SessionTrialProgressState) {
  const block = currentBlock(session);
  if (block === null) {
    return null;
  }

  return block.trials[session.currentTrialIndex] ?? null;
}

export function collectImageUrls(bootstrap: SessionBootstrap) {
  const imageUrls = new Set<string>();

  for (const block of bootstrap.blocks) {
    for (const trial of block.trials) {
      if (trial.stimulus.image_url !== null) {
        imageUrls.add(trial.stimulus.image_url);
      }
    }
  }

  return [...imageUrls];
}

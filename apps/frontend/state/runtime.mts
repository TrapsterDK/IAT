export function createRuntimeState() {
  return {
    assets: {
      imageObjectUrls: new Map<string, string>(),
    },
    catalog: {
      items: [],
      error: null,
      loading: false,
      startingIatSlug: null,
    },
    device: {
      prefersTouchInput: detectTouchInputPreference(),
    },
    session: null,
    ui: {
      screenError: null,
    },
  };
}

function detectTouchInputPreference() {
  return navigator.maxTouchPoints > 0 && window.matchMedia("(pointer: coarse)").matches;
}

const LEFT_RESPONSE_SIDE = 0;

export function createIatDetailFixture() {
  return {
    categories: [
      {
        category: [
          { label: "Alpha", slug: "alpha", stimuli: [{ image_url: null, text: "alpha" }] },
          { label: "Beta", slug: "beta", stimuli: [{ image_url: null, text: "beta" }] },
        ],
      },
      {
        category: [
          { label: "Good", slug: "good", stimuli: [{ image_url: null, text: "good" }] },
          { label: "Bad", slug: "bad", stimuli: [{ image_url: null, text: "bad" }] },
        ],
      },
    ],
    description: "Measures one sample association.",
    slug: "sample-iat",
    title: "Sample IAT",
  };
}

export function createBootstrapFixture() {
  return {
    blocks: [
      {
        is_practice: true,
        left_labels: ["Alpha"],
        right_labels: ["Beta"],
        trials: [
          {
            correct_response_side: LEFT_RESPONSE_SIDE,
            stimulus: { image_url: null, text: "alpha" },
          },
        ],
      },
    ],
    session_key: "session-1",
  };
}

FROM mcr.microsoft.com/devcontainers/base:ubuntu@sha256:4bcb1b466771b1ba1ea110e2a27daea2f6093f9527fb75ee59703ec89b5561cb

ARG DEBIAN_FRONTEND=noninteractive
ARG OPENCODE_VERSION=1.14.37
ARG BAZELISK_VERSION=1.29.0
ARG BAZELISK_AMD64_SHA256=5a408715e932c0250d28bd84555f12edbf70117de42f9181691c736eacc4a992
ARG BAZELISK_ARM64_SHA256=e20e8b0f4f240091b7a55bf17b9398bd4f40ee70ae0208dff95dd4c445fb4010

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install container-level runtime dependencies and standard devcontainer tools.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    direnv \
    fonts-liberation \
    gh \
    git \
    libasound2t64 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libdbus-1-3 \
    libegl1 \
    libfontconfig1 \
    libgbm1 \
    libgl1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libsm6 \
    libwayland-cursor0 \
    libwayland-egl1 \
    libx11-6 \
    libx11-xcb1 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-keysyms1 \
    libxcb-shape0 \
    libxcb-xinerama0 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxi6 \
    libxinerama1 \
    libxkbcommon-x11-0 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    patch \
    ripgrep \
    unzip \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

RUN arch="$(dpkg --print-architecture)" \
    && case "$arch" in \
        amd64) bazelisk_sha256="$BAZELISK_AMD64_SHA256" ;; \
        arm64) bazelisk_sha256="$BAZELISK_ARM64_SHA256" ;; \
        *) echo "Unsupported architecture: $arch" >&2; exit 1 ;; \
    esac \
    && curl -fsSL "https://github.com/bazelbuild/bazelisk/releases/download/v${BAZELISK_VERSION}/bazelisk-linux-${arch}" -o /usr/local/bin/bazel \
    && echo "${bazelisk_sha256}  /usr/local/bin/bazel" | sha256sum -c - \
    && chmod 0755 /usr/local/bin/bazel

RUN install -d -m 700 -o vscode -g vscode \
    /home/vscode/.cache \
    /home/vscode/.config \
    /home/vscode/.local \
    /home/vscode/.local/share \
    /home/vscode/.local/state

# Install OpenCode as the `vscode` user so it lands in /home/vscode/.opencode.
USER vscode
RUN curl -fsSL https://opencode.ai/install | bash -s -- --version "$OPENCODE_VERSION" --no-modify-path

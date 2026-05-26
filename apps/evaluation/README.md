# Evaluation

Run browser evaluations through Selenium Grid.

## Grid host

This runner connects to one Selenium Grid router via `--grid-url`.

If you are working in this repository, prepare the default Bazel environment first so `selenium-server` is on the tool path:

```bash
bazel run //tools:env
```

Then start the hub with:

```bash
selenium-server hub
```

See the [Selenium Grid getting started guide](https://www.selenium.dev/documentation/grid/getting_started/) for more deployment options.

## Workers

If you are provisioning worker machines outside this repository, install:

- Java 11 or newer
- the target browser on each worker machine
- Selenium Server 4.44.0, which matches the version pinned in this repo

Example install:

```bash
curl -L -o selenium-server.jar \
  https://github.com/SeleniumHQ/selenium/releases/download/selenium-4.44.0/selenium-server-4.44.0.jar
```

Then use `java -jar selenium-server.jar` in place of `selenium-server` in the commands below.

Each worker must advertise both the browser it serves and its stable evaluation worker id through the node stereotype.

```bash
selenium-server node \
  --hub "http://GRID_HOST:4444" \
  --selenium-manager true \
  --detect-drivers false \
  --driver-configuration "stereotype={\"browserName\":\"chrome\",\"iat:workerId\":\"worker-a\"}"
```

```bash
selenium-server node \
  --hub "http://GRID_HOST:4444" \
  --selenium-manager true \
  --detect-drivers false \
  --driver-configuration "stereotype={\"browserName\":\"firefox\",\"iat:workerId\":\"worker-b\"}"
```

Change `iat:workerId` per machine and set `browserName` to the actual browser that node serves.

Verify:

```bash
curl "http://GRID_HOST:4444/status"
```

Each worker slot must expose a unique `iat:workerId`.

Each worker slot must also expose one non-blank `browserName`.

## Run

Start the backend:

```bash
bazel run //apps/backend:main
```

Then run a benchmark:

```bash
bazel run //apps/evaluation:main -- spec \
  resources/evaluation/baseline-text-text.yaml \
  --output-dir resources/evaluation-results/baseline-text-text \
  --app-url https://example.test/ \
  --grid-url http://GRID_HOST:4444
```

The runner snapshots workers once at startup, so boot workers before running the CLI.

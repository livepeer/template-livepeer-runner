# your-app-livepeer-runner

An app that runs on the **Livepeer network**. It is an ordinary aiohttp service; an orchestrator hosts it and clients call it through that orchestrator, paying per call. Your app stays a plain HTTP service, so you are never tied to us.

Start it with `docker compose up -d --build` and call it with `uv run client.py`.

## Start here

Done once, then delete this section:

1. **Rename the repo** to `<app>-livepeer-runner` (e.g. `comfyui-livepeer-runner`). GitHub does not carry a template's name over.
2. **Add the `livepeer-runner` topic** and mention Livepeer in the repo description. Neither is copied from the template either, and both are how people find your app.
3. **Change `APP_ID`** in [runner.py](runner.py) and [client.py](client.py) from `your-org/your-app`. It is what callers discover and match on, exactly, so it has to say what they get.
4. **Update** `name` in [pyproject.toml](pyproject.toml) and the copyright in [LICENSE](LICENSE).
5. **Write your app**: replace `/run` in [runner.py](runner.py) and the call in [client.py](client.py). Everything else stays as-is.

|              |                                    |
| ------------ | ---------------------------------- |
| App id       | `your-org/your-app`                |
| Runner mode  | single-shot (one session per call) |
| Registration | dynamic (the app self-registers)   |
| Transport    | HTTP (JSON)                        |
| Pricing      | fixed (one price per call)         |
| Port         | 8989                               |

## How it's wired

The app calls `register_runner` on startup and heartbeats until it exits; the orchestrator reverse-proxies callers to it and drops it when the heartbeats stop. The client discovers it with `runner_selector` and calls it with `call_runner`. Grep `# Livepeer:` in [runner.py](runner.py) and [client.py](client.py) to see all four calls; they are the only Livepeer-specific lines in the app.

The orchestrator is a **transparent reverse proxy**, so every endpoint you expose is passed through unchanged. Add routes freely.

**Single-shot** means the orchestrator reserves a session for one request and releases it when the response returns, so the client manages no session. **Fixed** pricing bills one flat price per call. If your work is long-running or streaming, see the examples repo for the persistent and metered alternatives.

## Run offchain (free)

Needs **Docker** and [**uv**](https://docs.astral.sh/uv/). No wallet, no funds.

```sh
docker compose up -d --build
curl -sk https://localhost:8935/discovery | jq '.[].runners[].app'   # confirm it registered
uv run client.py --input hello
docker compose down
```

## Run on-chain (paid)

Layer the overlay to add a remote signer and put the orchestrator on-chain, so each call carries a real payment. Beyond the offchain prerequisites you need:

- An **Ethereum RPC** (Arbitrum One by default).
- A **signer wallet** (the payer) with an on-chain deposit and reserve.
- An **orchestrator wallet** with ETH for gas to redeem tickets.
- Both as **keystore directories outside this repo**, mounted read-only.

```sh
cp .env.example .env   # fill in RPC, network, keystore paths, accounts, price
docker compose -f compose.yml -f compose.onchain.yml up -d --build
uv run client.py --input hello --signer http://localhost:7936
docker compose -f compose.yml -f compose.onchain.yml down
```

> [!WARNING]
> The signer runs with `-remoteSignerAllowNoAuth`, which signs for anyone who can reach it and spends your deposit. That is fine on a laptop and wrong anywhere else: authorize callers with `-remoteSignerWebhookUrl` before exposing it.

## Static registration instead

Dynamic registration suits apps that come and go. If yours is a fixed deployment, the orchestrator can instead be pointed at it: the operator adds your entry to a `runners.json` (see [runners.json.example](runners.json.example)) and health-polls you, and the app needs **no SDK and no Livepeer code at all**.

That also makes any language a first-class option: a Go, Rust, or Node service can be a runner as-is. One of the examples is nothing but an nginx config.

The trade is who configures it. Dynamic needs the orchestrator's `orchSecret`; static needs the operator to edit their config. Dynamic is the default here because it runs end to end on your own machine with neither.

## More examples

This template is deliberately minimal. [**livepeer/runner-app-examples**](https://github.com/livepeer/runner-app-examples) has the full set, one per idea: WebSocket and trickle transports for realtime, persistent sessions, metered per-second pricing, static registration, capacity fan-out, and proxying a hosted API.

Once your app is published, open a PR there adding one row to its [External examples](https://github.com/livepeer/runner-app-examples#external-examples) table so people can find it.

## Ship it to an orchestrator

CI builds the image on every push and publishes it to `ghcr.io/<owner>/<repo>` on `main` and `v*` tags, with no setup: the built-in token is enough. Pull requests build without publishing.

An operator then runs your app from that image, so give them the tag and the app id. No credentials are involved either way: publishing uses the built-in token, and pulling a package from a public repo needs no login.

If an operator's pull 404s, the package is private — check its visibility under the repo's Packages settings.

To publish elsewhere, set the repository variables `IMAGE_NAME` and `REGISTRY_USERNAME` plus the secret `REGISTRY_TOKEN`.

## Development

```sh
uvx pre-commit install      # format on commit
uvx pre-commit run --all-files
```

CI runs the same hooks, checks the compose file parses, and builds the image.

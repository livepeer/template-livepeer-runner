# your-app-livepeer-runner

An app that runs on the **Livepeer network**. You write an ordinary HTTP service; an orchestrator hosts it and acts as a **transparent reverse proxy**, so callers reach your endpoints unchanged while it handles discovery, sessions, and payment. Nothing about your app is Livepeer-specific beyond announcing itself at startup, so you are never tied to us.

This template is that, end to end and already working: a small aiohttp service, a client that calls it through an orchestrator, and compose files that run both locally.

```sh
docker compose up -d --build
uv run client.py --input hello
```

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

`/run` in [runner.py](runner.py) is an ordinary aiohttp handler. Around it, the app calls `register_runner` on startup and heartbeats until it exits, and the orchestrator drops it when the heartbeats stop. The client finds it with `runner_selector` and calls it with `call_runner`.

Grep `# Livepeer:` in [runner.py](runner.py) and [client.py](client.py) to see all four calls. They are the only Livepeer-specific lines in the whole template.

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

## Ship it to an orchestrator

CI builds the image on every push and publishes it to `ghcr.io/<owner>/<repo>` on `main` and `v*` tags, with no setup: the built-in token is enough. Pull requests build without publishing.

An operator then runs your app from that image, so give them the tag and the app id. No credentials are involved either way: publishing uses the built-in token, and pulling a package from a public repo needs no login.

If an operator's pull 404s, the package is private — check its visibility under the repo's Packages settings.

To publish to Docker Hub as well, set the repository variable `DOCKERHUB_NAMESPACE` and the secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`. GHCR keeps working either way.

## Development

```sh
uvx pre-commit install      # format on commit
uvx pre-commit run --all-files
```

CI runs the same hooks, checks the compose file parses, and builds the image.

## Beyond this template

This template picks the simplest option on every axis. The live runner supports more, and swapping any of these is a change to your registration, not a rewrite. The [live runner docs](https://github.com/livepeer/go-livepeer/blob/master/doc/live-runner.md) are the reference.

- **Transports.** Plain HTTP here. Also **SSE** for streamed responses, **WebSocket** for long-lived sessions, and **trickle**, Livepeer's realtime media protocol, built to traverse firewalls. The orchestrator passes all of them through unchanged.
- **Modes.** `single-shot` here: one session per request, released when the response returns, so the client manages nothing. `persistent` instead lets a client reserve a session, use it as long as it needs, then release it — what realtime and stateful apps want.
- **Pricing.** `fixed` here, one flat payment per call. Also `hour`, quoted in USD per hour but metered per second while the session runs, and `720p` for video work.
- **Static registration.** Instead of self-registering, an operator can point a `runners.json` at your app (see [runners.json.example](runners.json.example)) and health-poll it. Then you need **no SDK and no Livepeer code at all**, so any language works: [`api-proxy`](https://github.com/livepeer/runner-app-examples/tree/main/api-proxy) is nothing but an nginx config, and [`vllm`](https://github.com/livepeer/runner-app-examples/tree/main/vllm) attaches the stock `vllm/vllm-openai` image untouched. The trade is who configures it: dynamic needs the orchestrator's `orchSecret`, static needs the operator to edit their config.

[**livepeer/runner-app-examples**](https://github.com/livepeer/runner-app-examples) has a working example of each. Once your app is published, open a PR there adding one row to its [External examples](https://github.com/livepeer/runner-app-examples#external-examples) table so people can find it.

# Deployment Learnings & Network Challenges

## Overview
This document records the deployment process and network-related challenges encountered during the setup of the `message-decoder` infrastructure, specifically targeting Liara, Vercel, and Cloudflare Workers (Telegram worker).

## Deployments

### 1. Vercel (Frontend)
- **Action**: Executed `vercel --prod` to build and deploy the Next.js frontend (`apps/web/out`).
- **Result**: **Success**. The project built successfully using Next.js 16.2.6 (Turbopack) and was published to Vercel CDN at `https://message-decoder-hmwhihihy-amirali6020s-projects.vercel.app` (Aliased: `https://message-decoder.vercel.app`).
- **Notes**: Vercel handles the Next.js static export very well. The configuration in `vercel.json` and `.vercelignore` correctly targeted the `apps/web/out` directory.

### 2. Liara (Backend / Full App)
- **Action**: Ran `npm run build:web` locally, which successfully compiled the static assets. Then executed:
  `liara deploy --app message-decoder-py --path . --dockerfile Dockerfile --port 8000 --build-arg NEXT_PUBLIC_API_URL= --message "automated deployment" --debug`
- **Result**: **Failed** due to network timeouts.
- **Error Details**: `TimeoutError: Timeout awaiting 'request' for 10000ms`.
- **Learnings**: 
  - Deploying to Liara from a local machine in heavily restricted networks (like Iran) can suffer from CLI upload timeouts. 
  - **Workaround/Fix**: The `liara-cli` needs a stable network. Sometimes using a local mirror proxy or VPN can help the CLI upload the code. In CI/CD pipelines, this is usually mitigated because GitHub Actions servers have reliable connections to Liara's endpoints.
  - Furthermore, `Dockerfile` properly uses the Liara PyPI mirror (`https://package-mirror.liara.ir/repository/pypi/simple`), but the deployment failed before the build phase even started, during the source code upload/request.

### 3. Cloudflare Workers / Telegram Worker
- **Action**: Attempted to deploy the worker using `cd apps/telegram-worker && CI=1 npx wrangler deploy`.
- **Result**: **Failed** initially due to `npm` cache issues (`npm error ENOTEMPTY: directory not empty, rename ... @cloudflare/workerd-darwin-arm64`).
- **Learnings**:
  - `npx` occasionally fails with `ENOTEMPTY` when trying to download large binaries like `workerd` if the npm cache is corrupted or blocked midway (likely due to network restrictions or interruptions).
  - **Workaround/Fix**: Installing Wrangler locally as a dev dependency (`npm i wrangler --no-save`) successfully bypassed the global cache locking issues and completed after about a minute. Cloudflare APIs also frequently require VPNs if routing from Iran is blocked.

## General Network Configuration
- It is vital to separate the `NEXT_PUBLIC_API_URL` based on whether the app is running on Vercel or Liara.
- `CORS_ORIGINS` on the Liara backend must explicitly include the Vercel production and preview domains.
- When working with Telegram bots and Cloudflare in a restricted network, utilizing Cloudflare Workers is necessary to bypass local server restrictions, but the *deployment* of the worker itself requires a solid connection to Cloudflare's API.

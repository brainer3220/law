<a href="https://chat.vercel.ai/">
  <img alt="Next.js 14 and App Router-ready AI chatbot." src="app/(chat)/opengraph-image.png">
  <h1 align="center">Chat SDK</h1>
</a>

<p align="center">
    Chat SDK is a free, open-source template built with Next.js and the AI SDK that helps you quickly build powerful chatbot applications.
</p>

<p align="center">
  <a href="https://chat-sdk.dev"><strong>Read Docs</strong></a> ·
  <a href="#features"><strong>Features</strong></a> ·
  <a href="#model-providers"><strong>Model Providers</strong></a> ·
  <a href="#deploy-your-own"><strong>Deploy Your Own</strong></a> ·
  <a href="#running-locally"><strong>Running locally</strong></a>
</p>
<br/>

## Features

- [Next.js](https://nextjs.org) App Router
  - Advanced routing for seamless navigation and performance
  - React Server Components (RSCs) and Server Actions for server-side rendering and increased performance
- [AI SDK](https://ai-sdk.dev/docs/introduction)
  - Unified API for generating text, structured objects, and tool calls with LLMs
  - Hooks for building dynamic chat and generative user interfaces
  - Supports xAI (default), OpenAI, Fireworks, and other model providers
- [shadcn/ui](https://ui.shadcn.com)
  - Styling with [Tailwind CSS](https://tailwindcss.com)
  - Component primitives from [Radix UI](https://radix-ui.com) for accessibility and flexibility
- Data Persistence
  - [Neon Serverless Postgres](https://vercel.com/marketplace/neon) for saving chat history and user data
  - [Vercel Blob](https://vercel.com/storage/blob) for efficient file storage
- [Auth.js](https://authjs.dev)
  - Simple and secure authentication
- Law MCP integration for Korean legal research (keyword search, statute detail, 법령해석례 조회)

## Model Providers

This template targets the local OpenAI-compatible gateway served by `uv run main.py serve --host 127.0.0.1 --port 8080`. By default the frontend sends requests to `http://127.0.0.1:8080/v1`. Override or secure the endpoint with the following environment variables:

- `OPENAI_COMPATIBLE_BASE_URL` – optional base URL override when the gateway is hosted elsewhere.
- `OPENAI_COMPATIBLE_API_KEY` – optional bearer token if the gateway enforces authentication.
- `OPENAI_COMPATIBLE_MODEL` (plus the `*_REASONING`, `*_TITLE`, `*_ARTIFACT` variants) – optional model IDs forwarded in the `model` field.

You can still swap in any other provider supported by the [AI SDK](https://ai-sdk.dev/providers/ai-sdk-providers) by editing `lib/ai/providers.ts`.

### Manual Gateway Check

Once the backend gateway is running you can issue a quick curl to confirm streaming responses:

```bash
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5-mini-2025-08-07",
    "messages": [{"role":"user","content":"근로시간 면제업무 관련 판례 알려줘"}],
    "stream": true
  }'
```

## Deploy Your Own

You can deploy your own version of the Next.js AI Chatbot to Vercel with one click:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/templates/next.js/nextjs-ai-chatbot)

## Running locally

You will need to use the environment variables [defined in `.env.example`](.env.example) to run Next.js AI Chatbot. It's recommended you use [Vercel Environment Variables](https://vercel.com/docs/projects/environment-variables) for this, but a `.env` file is all that is necessary.

> Note: You should not commit your `.env` file or it will expose secrets that will allow others to control access to your various AI and authentication provider accounts.

1. Install Vercel CLI: `npm i -g vercel`
2. Link local instance with Vercel and GitHub accounts (creates `.vercel` directory): `vercel link`
3. Download your environment variables: `vercel env pull`

### Built-in law tool endpoint

Legal research tools are now served directly from the OpenAI-compatible gateway started by `uv run law-cli serve`. Make sure the gateway is running before starting the Next.js dev server:

```bash
uv run law-cli serve --host 127.0.0.1 --port 8080
```

The frontend issues POST requests to `http://127.0.0.1:8080/v1/law/tools/<tool-name>` (or the URL specified via `LAW_TOOL_BASE_URL`) to resolve keyword, statute, and 법령해석례 lookups. If the gateway lives elsewhere, override the base URL with:

- `LAW_TOOL_BASE_URL` – explicit base URL for tool calls (defaults to `OPENAI_COMPATIBLE_BASE_URL`).
- `OPENAI_COMPATIBLE_BASE_URL` – reused when the explicit tool base is not provided.

```bash
pnpm install
pnpm dev
```

The dev server listens on [http://127.0.0.1:8080](http://127.0.0.1:8080) by default.

> ⚠️ The chat UI now requires an authenticated session. After launching the dev server, visit [`/register`](http://localhost:3000/register) to create an account before opening the chat interface. Any API requests made without a session cookie will return a `401 Unauthorized` response or redirect you back to the login page.

After signing in you can visit [`/mcp`](http://localhost:3000/mcp) to trigger the MCP-enabled completion demo without disturbing existing chat threads.

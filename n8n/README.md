# Orchestration and Networking Setup

## 1. Local Orchestration with n8n

n8n allows you to create event-driven workflows. For our architecture, you can use n8n to listen for webhook triggers from the frontend and orchestrate recalculation requests to our local Flask API.

### Setup Instructions
1. Make sure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
2. Open a terminal in this `n8n` directory.
3. Run `docker-compose up -d` to start the n8n container.
4. Open your browser and go to `http://localhost:5678`.
5. Create a new account (local).
6. **Create a Workflow:**
   - Add a "Webhook" node (method: POST). This gives you a URL (e.g., `http://localhost:5678/webhook/schedule`).
   - Add an "HTTP Request" node. Configure it to make a POST request to your local Flask API: `http://host.docker.internal:5000/api/schedule` (using `host.docker.internal` allows the container to reach your host's localhost).
   - Link the Webhook node to the HTTP Request node.
   - Activate the workflow. Now, your Next.js frontend can call the n8n webhook URL instead of the Flask API directly!

## 2. Secure Tunneling (Phase 4)

To deploy your Next.js app to Vercel (the cloud), it needs to be able to talk to your local backend API (Flask or n8n). We achieve this using a secure tunnel.

### Option A: Cloudflare Tunnels (Recommended, Free)
1. Install [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/).
2. Run the command: `cloudflared tunnel --url http://localhost:5000` (to expose Flask) or `http://localhost:5678` (to expose n8n).
3. Cloudflare will give you a public URL (e.g., `https://random-words.trycloudflare.com`).
4. In your Next.js app on Vercel, set an environment variable (e.g., `NEXT_PUBLIC_API_URL`) to this Cloudflare URL, and update `page.tsx` to use this environment variable instead of `http://localhost:5000`.

### Option B: Tailscale
1. Install [Tailscale](https://tailscale.com/) on your local machine and log in.
2. Enable Tailscale Funnel or just use your Tailscale IP if you also run a Tailscale client in the cloud (though Cloudflare is much easier for public Vercel apps).

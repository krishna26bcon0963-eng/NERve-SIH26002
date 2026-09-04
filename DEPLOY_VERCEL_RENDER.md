# NERve — Vercel + Render deployment

## 1. Backend (Render)
Create a Render Web Service from the `backend` folder.

Build command:
`pip install -r requirements.txt`

Start command:
`uvicorn main:app --host 0.0.0.0 --port $PORT`

Environment:
`FRONTEND_ORIGINS=https://YOUR-APP.vercel.app`

After deploy, copy the Render URL, for example:
`https://nerve-backend.onrender.com`

## 2. Frontend (Vercel)
Import the repository and set the project root to `frontend`.

Build command:
`npm run build`

Output directory:
`dist`

Environment variables:
`VITE_API_URL=https://YOUR-BACKEND.onrender.com`
`VITE_WS_URL=wss://YOUR-BACKEND.onrender.com`

Deploy.

## 3. Final check
Open the Vercel URL and test:
- map loads
- route search
- AI risk analysis
- backend API calls
- WebSocket/live features
- GPS
- external routing/weather calls

Do not put secret API keys in Vite `VITE_*` variables; those are exposed to the browser.

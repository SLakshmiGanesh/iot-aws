# Local setup
Requirements: Docker Desktop with Compose, or Python 3.12 and Node 22.
Run `docker compose up --build`, then open http://localhost:5173 and API docs at http://localhost:8000/docs. Local mode seeds demo readings into SQLite; it makes no AWS connection. For manual setup, install backend requirements then run `uvicorn app.main:app --app-dir backend --reload`; in another terminal run `cd frontend && npm install && npm run dev`.

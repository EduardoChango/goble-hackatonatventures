"""Flask BFF (backend-for-frontend): adapter de entrada HTTP para la UI."""

from flask import Flask, jsonify, request

from bff.backend_gateway import BackendError, build_backend

app = Flask(__name__)
backend = build_backend()


@app.errorhandler(BackendError)
def handle_backend_error(exc: BackendError):
    return jsonify({"error": str(exc)}), exc.status_code


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/jobs")
def create_job():
    return jsonify(backend.create_job(request.get_json(force=True) or {})), 201


@app.get("/api/jobs/<job_id>")
def get_job(job_id: str):
    return jsonify(backend.get_job(job_id))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

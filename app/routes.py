from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app import db
from app.models import AIRequest
from app.orchestrator import Orchestrator
from app.decision import make_decision

api_bp = Blueprint('api', __name__)
orchestrator = Orchestrator()


@api_bp.route('/ai/task', methods=['POST'])
def ai_task():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    task = data.get('task')
    text = data.get('text')
    provider = data.get('provider', 'auto')

    if not task or not text:
        return jsonify({"error": "'task' and 'text' are required"}), 400

    result = orchestrator.execute(task, text, preferred_provider=provider)

    # Determine status
    if result.get('provider_used') is None:
        status = 'error'
    else:
        status = 'success'

    # Save to database
    record = AIRequest(
        task=task,
        input_text=text,
        provider=result.get('provider_used', ''),
        latency_ms=result.get('latency_ms', 0),
        status=status,
        result_summary=(result.get('result') or '')[:500],
        error_message=result.get('error'),
    )
    db.session.add(record)
    db.session.commit()

    if status == 'error':
        return jsonify(result), 503

    # Build response
    response = {
        "provider_used": result["provider_used"],
        "result": result["result"],
        "confidence": result["confidence"],
        "latency_ms": result["latency_ms"],
    }

    # Add decision output for applicable tasks
    decision = make_decision(task, text, result["result"])
    if decision:
        response["decision"] = decision

    return jsonify(response), 200


@api_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200


@api_bp.route('/metrics', methods=['GET'])
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@api_bp.route('/history', methods=['GET'])
def history():
    records = (
        AIRequest.query
        .order_by(AIRequest.timestamp.desc())
        .limit(50)
        .all()
    )
    return jsonify([r.to_dict() for r in records]), 200

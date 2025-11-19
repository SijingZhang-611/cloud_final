# browse_service.py
import json
import os

import boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
QUESTIONS_TABLE = os.environ.get("QUESTIONS_TABLE", "QuestionsTable")
questions_table = dynamodb.Table(QUESTIONS_TABLE)


def decimal_to_native(obj):
    if isinstance(obj, list):
        return [decimal_to_native(i) for i in obj]
    if isinstance(obj, dict):
        return {k: decimal_to_native(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj


def response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def handler(event, context):
    method = event.get("httpMethod")
    path = event.get("path", "")
    qs_params = event.get("queryStringParameters") or {}

    if method == "GET" and path == "/browse/latest":
        return latest_questions()

    if method == "GET" and path == "/browse/top":
        return top_questions()

    if method == "GET" and path == "/browse/search":
        q = qs_params.get("q", "") if qs_params else ""
        return search_questions(q)

    return response(404, {"message": "Not found in browse service"})


def _load_all_questions():
    res = questions_table.scan()
    items = res.get("Items", [])
    # handle pagination if needed (for class project usually fine)
    return items


def latest_questions(limit=20):
    items = _load_all_questions()
    items.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    items = items[:limit]
    return response(200, decimal_to_native(items))


def top_questions(limit=20):
    items = _load_all_questions()
    items.sort(key=lambda x: int(x.get("voteCount", 0)), reverse=True)
    items = items[:limit]
    return response(200, decimal_to_native(items))


def search_questions(keyword, limit=50):
    keyword = (keyword or "").lower().strip()
    if not keyword:
        return response(400, {"message": "q parameter required"})

    items = _load_all_questions()
    hits = []
    for q in items:
        title = (q.get("title") or "").lower()
        body = (q.get("body") or "").lower()
        if keyword in title or keyword in body:
            hits.append(q)
    hits = hits[:limit]
    return response(200, decimal_to_native(hits))

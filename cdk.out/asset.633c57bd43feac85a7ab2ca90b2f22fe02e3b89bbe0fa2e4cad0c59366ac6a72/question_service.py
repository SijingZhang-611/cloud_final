# question_service.py
import json
import os
import uuid
from datetime import datetime

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

    # POST /questions   -> create question
    if method == "POST" and path == "/questions":
        return create_question(event)

    # GET /questions    -> list all questions (optionally filter by tag)
    if method == "GET" and path == "/questions":
        tag = qs_params.get("tag") if qs_params else None
        return list_questions(tag)

    # GET /questions/{id}
    if method == "GET" and path.startswith("/questions/"):
        question_id = path.split("/")[-1]
        return get_question(question_id)

    # POST /questions/{id}/vote
    if method == "POST" and path.startswith("/questions/") and path.endswith("/vote"):
        # path format: /questions/{id}/vote
        parts = path.split("/")
        if len(parts) == 4:
            question_id = parts[2]
            return vote_question(question_id, event)

    return response(404, {"message": "Not found in question service"})


def create_question(event):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"message": "Invalid JSON"})

    user_id = body.get("userId")
    title = body.get("title")
    q_body = body.get("body")
    tags = body.get("tags") or []

    if not user_id or not title or not q_body:
        return response(400, {"message": "userId, title, body are required"})

    question_id = str(uuid.uuid4())
    item = {
        "questionId": question_id,
        "userId": user_id,
        "title": title,
        "body": q_body,
        "tags": tags,
        "createdAt": datetime.utcnow().isoformat(),
        "voteCount": 0,
    }
    questions_table.put_item(Item=item)
    return response(201, item)


def list_questions(tag=None):
    # simple full scan; fine for class project
    res = questions_table.scan()
    items = res.get("Items", [])
    if tag:
        items = [i for i in items if tag in (i.get("tags") or [])]
    # sort newest first
    items.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    return response(200, decimal_to_native(items))


def get_question(question_id):
    res = questions_table.get_item(Key={"questionId": question_id})
    item = res.get("Item")
    if not item:
        return response(404, {"message": "Question not found"})
    return response(200, decimal_to_native(item))


def vote_question(question_id, event):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        body = {}
    delta = body.get("delta", 1)

    # update voteCount atomically
    try:
        questions_table.update_item(
            Key={"questionId": question_id},
            UpdateExpression="SET voteCount = if_not_exists(voteCount, :zero) + :delta",
            ExpressionAttributeValues={
                ":delta": Decimal(str(delta)),
                ":zero": Decimal("0"),
            },
        )
    except Exception as e:
        return response(500, {"message": "Failed to vote", "error": str(e)})

    # return updated item
    res = questions_table.get_item(Key={"questionId": question_id})
    item = res.get("Item")
    return response(200, decimal_to_native(item))

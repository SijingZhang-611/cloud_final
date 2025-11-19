# answer_service.py
import json
import os
import uuid
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
ANSWERS_TABLE = os.environ.get("ANSWERS_TABLE", "AnswersTable")
answers_table = dynamodb.Table(ANSWERS_TABLE)


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

    # POST /questions/{id}/answers
    if method == "POST" and path.startswith("/questions/") and path.endswith("/answers"):
        parts = path.split("/")
        # /questions/{id}/answers -> ["", "questions", "{id}", "answers"]
        if len(parts) == 4:
            question_id = parts[2]
            return create_answer(question_id, event)

    # GET /questions/{id}/answers
    if method == "GET" and path.startswith("/questions/") and path.endswith("/answers"):
        parts = path.split("/")
        if len(parts) == 4:
            question_id = parts[2]
            return list_answers(question_id)

    # POST /answers/{id}/vote
    if method == "POST" and path.startswith("/answers/") and path.endswith("/vote"):
        # /answers/{id}/vote -> ["", "answers", "{id}", "vote"]
        parts = path.split("/")
        if len(parts) == 4:
            answer_id = parts[2]
            return vote_answer(answer_id, event)

    return response(404, {"message": "Not found in answer service"})


def create_answer(question_id, event):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"message": "Invalid JSON"})

    user_id = body.get("userId")
    a_body = body.get("body")

    if not user_id or not a_body:
        return response(400, {"message": "userId and body are required"})

    answer_id = str(uuid.uuid4())
    item = {
        "answerId": answer_id,
        "questionId": question_id,
        "userId": user_id,
        "body": a_body,
        "createdAt": datetime.utcnow().isoformat(),
        "voteCount": 0,
    }
    answers_table.put_item(Item=item)
    return response(201, item)


def list_answers(question_id):
    # You should create a GSI on questionId for AnswersTable
    res = answers_table.query(
        IndexName="QuestionIdIndex",  # define GSI with PK = questionId
        KeyConditionExpression=Key("questionId").eq(question_id),
    )
    items = res.get("Items", [])
    items.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    return response(200, decimal_to_native(items))


def vote_answer(answer_id, event):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        body = {}
    delta = body.get("delta", 1)

    try:
        answers_table.update_item(
            Key={"answerId": answer_id},
            UpdateExpression="SET voteCount = if_not_exists(voteCount, :zero) + :delta",
            ExpressionAttributeValues={
                ":delta": Decimal(str(delta)),
                ":zero": Decimal("0"),
            },
        )
    except Exception as e:
        return response(500, {"message": "Failed to vote", "error": str(e)})

    res = answers_table.get_item(Key={"answerId": answer_id})
    item = res.get("Item")
    return response(200, decimal_to_native(item))

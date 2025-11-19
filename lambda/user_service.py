# user_service.py
import json
import os
import uuid
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
USERS_TABLE = os.environ.get("USERS_TABLE", "UsersTable")
users_table = dynamodb.Table(USERS_TABLE)


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

    if method == "POST" and path == "/users":
        return create_user(event)
    if method == "GET" and path.startswith("/users/"):
        user_id = path.split("/")[-1]
        return get_user(user_id)

    return response(404, {"message": "Not found in user service"})


def create_user(event):
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"message": "Invalid JSON"})

    username = body.get("username")
    email = body.get("email")
    if not username:
        return response(400, {"message": "username is required"})

    user_id = str(uuid.uuid4())
    item = {
        "userId": user_id,
        "username": username,
        "email": email or "",
        "createdAt": datetime.utcnow().isoformat(),
    }
    users_table.put_item(Item=item)
    return response(201, item)


def get_user(user_id):
    res = users_table.get_item(Key={"userId": user_id})
    item = res.get("Item")
    if not item:
        return response(404, {"message": "User not found"})
    return response(200, decimal_to_native(item))

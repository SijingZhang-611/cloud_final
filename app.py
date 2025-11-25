#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.storage_stack import StorageStack
from stacks.service_stack import ServiceStack
from stacks.api_stack import ApiStack

app = cdk.App()

env = cdk.Environment(account="024848456788", region="us-east-1")

storage = StorageStack(app, "StorageStack", env=env)
services = ServiceStack(app, "ServiceStack", tables=storage.tables, env=env)
api = ApiStack(app, "ApiStack", lambdas=services.lambdas, env=env)

app.synth()

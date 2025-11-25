from aws_cdk import (
    Stack,
    aws_dynamodb as ddb,
)
from constructs import Construct

class StorageStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        questions = ddb.Table(
            self, "QuestionsTable",
            table_name="QuestionsTable",
            partition_key=ddb.Attribute(name="questionId", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
        )

        answers = ddb.Table(
            self, "AnswersTable",
            table_name="AnswersTable",
            partition_key=ddb.Attribute(name="answerId", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
        )

        # ✅ NEW: GSI used by answer_service.list_answers
        answers.add_global_secondary_index(
            index_name="QuestionIdIndex",
            partition_key=ddb.Attribute(name="questionId", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.ALL,
        )

        users = ddb.Table(
            self, "UsersTable",
            table_name="UsersTable",
            partition_key=ddb.Attribute(name="userId", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
        )

        self.tables = {
            "questions": questions,
            "answers": answers,
            "users": users,
        }

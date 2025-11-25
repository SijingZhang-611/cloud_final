from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
)
from constructs import Construct

class ServiceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, tables, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.question_fn = _lambda.Function(
            self, "QuestionServiceFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="question_service.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "QUESTIONS_TABLE": tables["questions"].table_name,
                "ANSWERS_TABLE": tables["answers"].table_name,
                "USERS_TABLE": tables["users"].table_name,
            },
        )
        tables["questions"].grant_read_write_data(self.question_fn)
        tables["answers"].grant_read_write_data(self.question_fn)
        tables["users"].grant_read_write_data(self.question_fn)

        self.answer_fn = _lambda.Function(
            self, "AnswerServiceFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="answer_service.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "ANSWERS_TABLE": tables["answers"].table_name,
            },
        )
        tables["answers"].grant_read_write_data(self.answer_fn)

        self.browse_fn = _lambda.Function(
            self, "BrowseServiceFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="browse_service.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "QUESTIONS_TABLE": tables["questions"].table_name,
            },
        )
        tables["questions"].grant_read_data(self.browse_fn)

        self.user_fn = _lambda.Function(
            self, "UserServiceFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="user_service.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "USERS_TABLE": tables["users"].table_name,
            },
        )
        tables["users"].grant_read_write_data(self.user_fn)

        # expose Lambdas to other stacks
        self.lambdas = {
            "questions": self.question_fn,
            "answers": self.answer_fn,
            "browse": self.browse_fn,
            "users": self.user_fn,
        }

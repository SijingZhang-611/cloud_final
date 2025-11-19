from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_dynamodb as ddb,
    aws_apigateway as apigw,
)


class QaLiteStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1) DynamoDB tables
        users_table = ddb.Table(
            self,
            "UsersTable",
            table_name="UsersTable",
            partition_key=ddb.Attribute(name="userId", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,  # for class/demo
        )

        questions_table = ddb.Table(
            self,
            "QuestionsTable",
            table_name="QuestionsTable",
            partition_key=ddb.Attribute(name="questionId", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        answers_table = ddb.Table(
            self,
            "AnswersTable",
            table_name="AnswersTable",
            partition_key=ddb.Attribute(name="answerId", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # GSI for querying answers by questionId
        answers_table.add_global_secondary_index(
            index_name="QuestionIdIndex",
            partition_key=ddb.Attribute(name="questionId", type=ddb.AttributeType.STRING),
        )

        # 2) Lambda functions (point to your code in lambda/)
        user_fn = _lambda.Function(
            self,
            "UserServiceFunction",
            function_name="UserServiceFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="user_service.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "USERS_TABLE": users_table.table_name,
            },
            timeout=Duration.seconds(30),
        )

        question_fn = _lambda.Function(
            self,
            "QuestionServiceFunction",
            function_name="QuestionServiceFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="question_service.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "QUESTIONS_TABLE": questions_table.table_name,
            },
            timeout=Duration.seconds(30),
        )

        answer_fn = _lambda.Function(
            self,
            "AnswerServiceFunction",
            function_name="AnswerServiceFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="answer_service.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "ANSWERS_TABLE": answers_table.table_name,
            },
            timeout=Duration.seconds(30),
        )

        browse_fn = _lambda.Function(
            self,
            "BrowseServiceFunction",
            function_name="BrowseServiceFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="browse_service.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "QUESTIONS_TABLE": questions_table.table_name,
            },
            timeout=Duration.seconds(30),
        )

        # Permissions: lambdas can access their tables
        users_table.grant_read_write_data(user_fn)
        questions_table.grant_read_write_data(question_fn)
        answers_table.grant_read_write_data(answer_fn)
        questions_table.grant_read_data(browse_fn)

        # 3) API Gateway REST API
        api = apigw.RestApi(
            self,
            "QaLiteApi",
            rest_api_name="QaLiteApi",
            deploy_options=apigw.StageOptions(stage_name="prod"),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            ),
        )

        # Integrations
        user_integration = apigw.LambdaIntegration(user_fn)
        question_integration = apigw.LambdaIntegration(question_fn)
        answer_integration = apigw.LambdaIntegration(answer_fn)
        browse_integration = apigw.LambdaIntegration(browse_fn)

        # /users
        users_res = api.root.add_resource("users")
        users_res.add_method("POST", user_integration)  # create user
        user_id_res = users_res.add_resource("{id}")
        user_id_res.add_method("GET", user_integration)  # get user

        # /questions
        questions_res = api.root.add_resource("questions")
        questions_res.add_method("POST", question_integration)  # create question
        questions_res.add_method("GET", question_integration)   # list questions

        question_id_res = questions_res.add_resource("{id}")
        question_id_res.add_method("GET", question_integration)  # get question

        # /questions/{id}/vote   -> Question service
        question_vote_res = question_id_res.add_resource("vote")
        question_vote_res.add_method("POST", question_integration)

        # /questions/{id}/answers -> Answer service
        q_answers_res = question_id_res.add_resource("answers")
        q_answers_res.add_method("GET", answer_integration)
        q_answers_res.add_method("POST", answer_integration)

        # /answers/{id}/vote -> Answer service
        answers_res = api.root.add_resource("answers")
        answer_id_res = answers_res.add_resource("{id}")
        answer_vote_res = answer_id_res.add_resource("vote")
        answer_vote_res.add_method("POST", answer_integration)

        # /browse/latest, /browse/top, /browse/search -> Browse service
        browse_res = api.root.add_resource("browse")
        latest_res = browse_res.add_resource("latest")
        latest_res.add_method("GET", browse_integration)

        top_res = browse_res.add_resource("top")
        top_res.add_method("GET", browse_integration)

        search_res = browse_res.add_resource("search")
        search_res.add_method("GET", browse_integration)

        # Output the API URL for convenience
        cdk.CfnOutput(
            self,
            "ApiUrl",
            value=api.url,
            description="Base URL of the Q&A Lite API",
        )

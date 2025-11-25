from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
)
from constructs import Construct

class ApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, lambdas, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        api = apigw.RestApi(
            self, "QaLiteApi",
            rest_api_name="QaLiteApi",
            deploy_options=apigw.StageOptions(stage_name="prod"),
            # optional but recommended CORS:
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["*"],
            ),
        )

        # -------- questions --------
        q_res = api.root.add_resource("questions")
        # POST /questions  -> create question
        q_res.add_method("POST", apigw.LambdaIntegration(lambdas["questions"]))
        # GET /questions   -> list questions (question_service supports this)
        q_res.add_method("GET", apigw.LambdaIntegration(lambdas["questions"]))

        # /questions/{id}
        single_q = q_res.add_resource("{id}")
        # GET /questions/{id}  (optional, but supported by question_service)
        single_q.add_method("GET", apigw.LambdaIntegration(lambdas["questions"]))

        # /questions/{id}/answers  -> answer_service
        answers_res = single_q.add_resource("answers")
        answers_res.add_method("POST", apigw.LambdaIntegration(lambdas["answers"]))
        answers_res.add_method("GET", apigw.LambdaIntegration(lambdas["answers"]))

        # /questions/{id}/vote  -> question_service.vote_question
        vote_q = single_q.add_resource("vote")
        vote_q.add_method("POST", apigw.LambdaIntegration(lambdas["questions"]))

        # -------- answers (for voting answers) --------
        ans_root = api.root.add_resource("answers")
        ans_item = ans_root.add_resource("{id}")
        vote_a = ans_item.add_resource("vote")
        vote_a.add_method("POST", apigw.LambdaIntegration(lambdas["answers"]))

        # -------- users --------
        u_res = api.root.add_resource("users")
        u_res.add_method("POST", apigw.LambdaIntegration(lambdas["users"]))

        # -------- browse --------
        browse = api.root.add_resource("browse")
        latest = browse.add_resource("latest")
        latest.add_method("GET", apigw.LambdaIntegration(lambdas["browse"]))

        self.api_url = api.url

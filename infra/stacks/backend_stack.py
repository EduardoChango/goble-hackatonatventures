from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as _lambda
from constructs import Construct

ROOT = Path(__file__).resolve().parents[2]
LAMBDAS_DIR = ROOT / "apps" / "lambdas"
LAYER_DIR = ROOT / "build" / "layer"  # generado por scripts/build_layer.py


class BackendStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, *, env_name: str, use_mocks: bool, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        jobs_table = dynamodb.Table(
            self,
            "JobsTable",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # hackathon: cambiar a RETAIN en prod
        )

        # Layer con el core hexagonal (goble) + fixtures de mocks
        core_layer = _lambda.LayerVersion(
            self,
            "CoreLayer",
            code=_lambda.Code.from_asset(str(LAYER_DIR)),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="goble core (domain + application + adapters) y mocks",
        )

        environment = {
            "APP_ENV": env_name,
            "USE_MOCKS": str(use_mocks).lower(),
            "MOCKS_DIR": "/opt/mocks/external_apis",
            "JOBS_TABLE_NAME": jobs_table.table_name,
            # TODO: mover a Secrets Manager / SSM cuando se use la API real
            "PROVIDER_API_URL": "",
        }

        def make_function(construct_name: str, folder: str) -> _lambda.Function:
            return _lambda.Function(
                self,
                construct_name,
                runtime=_lambda.Runtime.PYTHON_3_12,
                handler="handler.handler",
                code=_lambda.Code.from_asset(str(LAMBDAS_DIR / folder)),
                layers=[core_layer],
                environment=environment,
                timeout=Duration.seconds(30),
                memory_size=256,
            )

        process_job_fn = make_function("ProcessJobFn", "process_job")
        get_job_fn = make_function("GetJobFn", "get_job")

        jobs_table.grant_read_write_data(process_job_fn)
        jobs_table.grant_read_data(get_job_fn)

        api = apigw.RestApi(
            self,
            "Api",
            rest_api_name=f"goble-{env_name}",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS, allow_methods=apigw.Cors.ALL_METHODS
            ),
        )
        jobs = api.root.add_resource("jobs")
        jobs.add_method("POST", apigw.LambdaIntegration(process_job_fn))
        jobs.add_resource("{job_id}").add_method("GET", apigw.LambdaIntegration(get_job_fn))

        self.api_url = api.url
        CfnOutput(self, "ApiUrl", value=api.url)
        CfnOutput(self, "JobsTableName", value=jobs_table.table_name)

#!/usr/bin/env python3
import os

import aws_cdk as cdk

from stacks.backend_stack import BackendStack
from stacks.frontend_stack import FrontendStack

app = cdk.App()

env_name = app.node.try_get_context("env") or "dev"
use_mocks = str(app.node.try_get_context("use_mocks") or "true").lower() == "true"
aws_env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION", "us-east-1")
)

backend = BackendStack(
    app, f"Goble-{env_name}-Backend", env_name=env_name, use_mocks=use_mocks, env=aws_env
)
FrontendStack(app, f"Goble-{env_name}-Frontend", api_url=backend.api_url, env=aws_env)

app.synth()

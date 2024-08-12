#!/usr/bin/env python3
import os

import aws_cdk as cdk

from rag_serverless.rag_serverless_stack import SecretManagerStack


app = cdk.App()
SecretManagerStack(app, "SecretManagerStack",)

app.synth()

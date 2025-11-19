#!/usr/bin/env python3
import aws_cdk as cdk

from qa_lite.qa_lite_stack import QaLiteStack


app = cdk.App()
QaLiteStack(app, "QaLiteStack")

app.synth()
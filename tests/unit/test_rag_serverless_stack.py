import aws_cdk as core
import aws_cdk.assertions as assertions

from rag_serverless.rag_serverless_stack import RagServerlessStack

# example tests. To run these tests, uncomment this file along with the example
# resource in rag_serverless/rag_serverless_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = RagServerlessStack(app, "rag-serverless")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })

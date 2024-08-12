from aws_cdk import (
    # Duration,
    Stack,
    aws_secretsmanager as secretsmanager,
    SecretValue,
    CfnOutput
)
from constructs import Construct
import os
from dotenv import load_dotenv


# Secrets ManagerにAPIキーを保存するスタック
class SecretManagerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        load_dotenv()
        pc_api_key = os.environ.get("PINECONE_API_KEY")

        # Secrets ManagerにAPIキーを保存
        secret = secretsmanager.Secret(
            self,
            "Secret",
            secret_name="pinecone",
            secret_object_value={
                "apiKey": SecretValue.unsafe_plain_text(pc_api_key),
            },
        )
        secret_arn = secret.secret_arn
        CfnOutput(self, "SecretArnOutput", value=secret_arn)

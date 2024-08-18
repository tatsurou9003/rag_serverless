from aws_cdk import (
    # Duration,
    Stack,
    Fn,
    aws_s3 as s3,
    aws_s3_deployment as s3d,
    aws_secretsmanager as secretsmanager,
    SecretValue,
    CfnOutput,
    RemovalPolicy,
    aws_bedrock as bedrock,
    aws_iam as iam,
)
from constructs import Construct
import os
from dotenv import load_dotenv

load_dotenv()


# Secrets ManagerにAPIキーを保存するスタック
class SecretManagerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

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
        CfnOutput(
            self, "SecretArnOutput", value=secret_arn, export_name="PineconeSecretArn"
        )


# BedrockKnowledgeBaseの諸々の設定を行うスタック
class BedrockKnowledgeBaseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ポリシー定義
        bedrock_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:*"],
            resources=["*"]
        )

        s3_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            resources=["arn:aws:s3:::your-bucket-name", "arn:aws:s3:::your-bucket-name/*"]
        )

        secrets_manager_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
            resources=["arn:aws:secretsmanager:*:*:secret:your-secret-name-*"]
        )

        # IAMロールの作成
        role = iam.Role(self, "MyBedrockRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Role for Bedrock with S3 and Secrets Manager access"
        )

        role.add_to_policy(bedrock_policy)
        role.add_to_policy(s3_policy)
        role.add_to_policy(secrets_manager_policy)

        # データソース用のバケットを作成
        kb_bucket = s3.Bucket(
            self,
            "KnowledgeBucket",
            bucket_name="knowledge-base-bucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # ファイルのアップロード
        s3d.BucketDeployment(self, "KnowledgeBaseDocs",
            sources=[s3d.Source.asset("./docs")], 
            destination_bucket=kb_bucket,
            destination_key_prefix="bedrock/",  
        )

        kb_bucket.grant_read_write(iam.ServicePrincipal("bedrock.amazonaws.com"))


        pc_index_endpoint = os.environ.get("PINECONE_INDEX_ENDPOINT")
        secret_arn = Fn.import_value("PineconeSecretArn")
        # BedrockKnowledgeBaseの作成
        bedrock_knowledge_base = bedrock.CfnKnowledgeBase(
            self,
            "MyCfnKnowledgeBase",
            name="ServerlessKnowledgeBase",
            description="サーバレス構成RAG用のKnowledgeBase",
            role_arn=role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn="arn:aws:bedrock:ap-northeast1::foundation-model/amazon.titan-embed-text-v1"
                ),
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="PINECONE",
                pinecone_configuration=bedrock.CfnKnowledgeBase.PineconeConfigurationProperty(
                    connection_string=pc_index_endpoint,
                    credentials_secret_arn=secret_arn,
                    field_mapping=bedrock.CfnKnowledgeBase.PineconeFieldMappingProperty(
                        metadata_field="metadataField", text_field="textField"
                    ),
                ),
            ),
        )

        # KnowledgeBase用のデータソースを設定
        kb_data_source = bedrock.CfnDataSource(
            self,
            "MyCfnDataSource",
            name="KbDataSource",
            knowledge_base_id=bedrock_knowledge_base.ref,
            description="KnowledgeBase用のS3データソース",
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=kb_bucket.bucket_arn,  
                    inclusion_prefixes=["bedrock"],
                ),
                type="S3",
            ),
            vector_ingestion_configuration=bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
                chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                    chunking_strategy="FIXED_SIZE",
                    fixed_size_chunking_configuration=bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
                        max_tokens=300, overlap_percentage=20
                    ),
                )
            ),
            data_deletion_policy="DELETE",
        )

        kb_data_source.node.add_dependency(bedrock_knowledge_base)

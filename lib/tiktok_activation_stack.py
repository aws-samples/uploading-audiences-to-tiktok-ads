import json
from constructs import Construct
from aws_cdk import App, Stack, Duration, Stack, CfnOutput, SecretValue
from aws_cdk.aws_sqs import QueueEncryption

from aws_cdk import (
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
    RemovalPolicy,
    Duration,
    aws_secretsmanager as secretsmanager,
    aws_events as events,
    aws_events_targets as targets,
    aws_sqs as _sqs,
    aws_lambda_destinations as _lambda_dest,
    Duration,
    aws_s3_deployment as s3_deploy,
)
from aws_cdk.aws_lambda_event_sources import SqsEventSource


class TikTokActivationStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.tiktok_data_bucket_name = self.node.try_get_context("tiktok_data_bucket_name")
        self.supported_calculate_types=self.node.try_get_context("supported_calculate_types")
        self.cred_secret_name=self.node.try_get_context("cred_secret_name")
        self.add_eventbridge_bus()
        self.add_buckets(self.tiktok_data_bucket_name)
        self.add_secret()
        self.add_queues()
        self.add_tiktok_lambda(self.tiktok_data_bucket_name)
        self.add_csv_data()

    ##############################################################################
    # S3 Buckets
    ##############################################################################

    def add_buckets(self, data_bucket_name):
        self.data_bucket = s3.Bucket(
            self,
            "s3_data_bucket",
            bucket_name=f"{data_bucket_name}",
            event_bridge_enabled=True,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True
        )
        CfnOutput(self, "s3-data-bucket-name",
                  value=self.data_bucket.bucket_name)
    
    ##############################################################################
    # Add Secret
    ##############################################################################    

    def add_secret(self):
        if (secretsmanager.Secret.from_secret_name_v2(self, "tiktok_activation_credentials_v1",  self.cred_secret_name)):
            self.tiktok_activation_secret = secretsmanager.Secret.from_secret_name_v2(self, "tiktok_activation_credentials_V2",  self.cred_secret_name)            
        else:            
            self.tiktok_activation_secret = secretsmanager.Secret(self, "tiktok_activation_credentials_v3",
                                                                secret_name=self.cred_secret_name,
                                                                description="tiktokads marketing api accesstoken and advertiserid",
                                                                removal_policy=RemovalPolicy.RETAIN,
                                                                generate_secret_string=secretsmanager.SecretStringGenerator(
                                                                    secret_string_template=json.dumps(
                                                                        {"credentials": ""}),
                                                                    generate_string_key="credentials"
                                                                )
                                                                )
            
    ##############################################################################
    # EventBridge
    ##############################################################################

    def add_eventbridge_bus(self):
        self.bus = events.EventBus.from_event_bus_arn(self, "default_event_bus",
                                                f"arn:aws:events:{self.region}:{self.account}:event-bus/default")

        self.bus.archive("activation_eventbridge_archive",
            archive_name="tiktok_activation_eventbridge_archive",
            description="tiktok Activation EventBridge Archive",
            event_pattern=events.EventPattern(
                account=[Stack.of(self).account],
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={"object": {"key": [{"prefix": "tiktok"}]}}
            ),
            retention=Duration.days(365)
        )

    
    ##############################################################################
    # Queues 
    ##############################################################################

    def add_queues(self):
        self.dead_letter_queue = _sqs.Queue(self, "tiktok_activator_connector_dlq",
                                            queue_name="tiktok_connector_dlq",
                                            encryption=QueueEncryption.KMS,
                                            data_key_reuse=Duration.days(1)
                                            )

        self.queue = _sqs.Queue(self, "tiktok_activator_connector",
                                queue_name="tiktok_connector",
                                encryption=QueueEncryption.KMS,
                                data_key_reuse=Duration.days(1),
                                visibility_timeout=Duration.minutes(90),
                                dead_letter_queue=_sqs.DeadLetterQueue(
                                    max_receive_count=5,
                                    queue=self.dead_letter_queue
                                )
                                )

        self.lambda_dest_failure_queue = _sqs.Queue(
            self,
            "tiktok_connector_dest_failure_queue",
            queue_name='tiktok_connector_dest_failure_queue',
            encryption=QueueEncryption.KMS
        )

    ##############################################################################
    # tiktok Lambda functions
    ##############################################################################

    def add_tiktok_lambda(self, data_bucket_name):
        s3_read_policy_stmt = iam.PolicyStatement(
            resources=["arn:aws:s3:::" + self.tiktok_data_bucket_name,
                       "arn:aws:s3:::" + self.tiktok_data_bucket_name + "/*"],
            actions=[
                'S3:ListBucket',
                'S3:GetObjectTagging',
                'S3:ListBucket',
                'S3:GetObject',
                'S3:PutBucketNotification',
            ]
        )
        
        


       # Activation for SQS
        self.tiktok_activation_lambda = _lambda.Function(self, 'tiktok-activation-lambda',
                                                           function_name=f'tiktok-activation-lambda',
                                                           handler='lambda-handler.lambda_handler',
                                                           runtime=_lambda.Runtime.PYTHON_3_9,
                                                           code=_lambda.Code.from_asset(
                                                               'lambdas/tiktok/activation'),
                                                           description="tiktok-activation to upload custom audience",
                                                           timeout=Duration.seconds(
                                                               900),
                                                           memory_size=256,
                                                           #insights_version=_lambda.LambdaInsightsVersion.from_insight_version_arn(layer_arn),
                                                           tracing=_lambda.Tracing.ACTIVE,
                                                           environment={
                                                            'S3_DATA_BUCKET': self.tiktok_data_bucket_name,
                                                            'CRED_SECRET_NAME': self.tiktok_activation_secret.secret_name, 
                                                            'SUPPORTED_CALCULATE_TYPES': self.supported_calculate_types 
                                                            },
                                                            layers=[_lambda.LayerVersion.from_layer_version_arn(self, "datawrangler-02",f'arn:aws:lambda:{self.region}:336392948345:layer:AWSDataWrangler-Python39:9')],
                                                          
                                                           on_failure=_lambda_dest.SqsDestination(
                                                               self.lambda_dest_failure_queue),
                                                           )

        # Add inline policy to the lambda
        self.tiktok_activation_lambda.add_to_role_policy(s3_read_policy_stmt)

        # Add read secret permissions for both secrets and write to oAuth
        self.tiktok_activation_secret.grant_read(self.tiktok_activation_lambda)


        # Add Permissions to lambda to write messages to queue
        self.lambda_dest_failure_queue.grant_send_messages(
            self.tiktok_activation_lambda)

        # Add SQS event source to the Lambda function
        self.tiktok_activation_lambda.add_event_source(SqsEventSource(self.queue,
            batch_size=1,
        ))
         # Enforce SSL
        self.lambda_dest_failure_queue.add_to_resource_policy(
            self.get_enforce_ssl_policy(self.lambda_dest_failure_queue.queue_arn)
        )
        # Route S3 Events to SQS from EventBridge

        event_consumer1_rule = events.Rule(self, 'tiktok_event_consumer_lambda_rule',
                                           description='S3 Event',
                                           event_pattern=events.EventPattern(
                                            source=["aws.s3"],
                                            detail_type=["Object Created"],
                                            detail={"object": {"key": [{"prefix": "tiktok"}]}},
                                        )
                                            )
        event_consumer1_rule.add_target(targets.SqsQueue(self.queue))
    ##############################################################################
    # tiktok sample custom audience
    ##############################################################################

    # sample data for testing
    def add_csv_data(self):
        s3_deploy.BucketDeployment(
            self,
            "data-deployment",
            sources=[s3_deploy.Source.asset("./test/tiktok")],
            destination_bucket=self.data_bucket,
            destination_key_prefix="tiktok/foodies-custom-audience/phone_sha256",
        )    

    def get_enforce_ssl_policy(self, queue_arn):
        return iam.PolicyStatement(
            sid='Enforce TLS for all principals',
            effect=iam.Effect.DENY,
            principals=[
                iam.AnyPrincipal(),
            ],
            actions=[
                'sqs:*',
            ],
            resources=[queue_arn],
            conditions={
                'Bool': {'aws:SecureTransport': 'false'},
            },
        )
#!/usr/bin/env python3
import os

import aws_cdk as cdk
from aws_cdk import App, Tags,Aspects
from lib.tiktok_activation_stack import TikTokActivationStack
from cdk_nag import AwsSolutionsChecks, NagSuppressions

app = cdk.App()
description='''
(SO9073) Solution guidance to assist AWS customers with automating the activation of TikTok Ads with custom audience data for selected TikTok Advertiser.
It explores the stages of activating custom audience segments data created in AWS to deliver personalized ads in TikTok
'''
tiktok_activate = TikTokActivationStack(app, "activation-connector-tiktok-stack", description=description)
cdk.Tags.of(tiktok_activate).add("project", "activation-connector-tiktok-stack")

NagSuppressions.add_stack_suppressions(
    tiktok_activate,
    [
        {
            "id": "AwsSolutions-IAM5",
            "reason": "AWS managed policies are allowed which sometimes uses * in the resources like - AWSGlueServiceRole has aws-glue-* . AWS Managed IAM policies have been allowed to maintain secured access with the ease of operational maintenance - however for more granular control the custom IAM policies can be used instead of AWS managed policies",
        },
        {
            "id": "AwsSolutions-IAM4",
            "reason": "AWS Managed IAM policies have been allowed to maintain secured access with the ease of operational maintenance - however for more granular control the custom IAM policies can be used instead of AWS managed policies",
        },
        {
            "id": "AwsSolutions-IAM4",
            "reason": "AWS Managed IAM policies have been allowed to maintain secured access with the ease of operational maintenance - however for more granular control the custom IAM policies can be used instead of AWS managed policies",
        },
        {
            "id": "AwsSolutions-S1",
            "reason": "S3 Access Logs are disabled for demo purposes.",
        },
        {
            "id": "AwsSolutions-SQS3",
            "reason": "DLQ is enabled on the queue.",
        },
        {
            "id": "AwsSolutions-SQS4",
            "reason": "SSL Transport is applied to Queue policy",
        },
        {
            'id': 'AwsSolutions-KMS5',
            'reason': 'SQS KMS key properties are not accessible from cdk',
        }
    ],
)

# Simple rule informational messaged
Aspects.of(app).add(AwsSolutionsChecks())
app.synth()

# Activation Connector for TikTok Ads

## Overview



Solution guidance to assist AWS customers with automating the activation of TikTok Ads with custom audience data for selected TikTok Advertiser. It explores the stages of activating custom audience segments data created in AWS to deliver personalized ads in TikTok.

The Activation Connector for TikTok Ads allows you to use enriched data in AWS to create targeted Custom Audiences in TikTok. With this connector, you can leverage user profile data to create Custom Audiences in TikTok in as custom file upload.
 

## Architecture Overview

With the Activation Connector for TikTok Ads, using an event-based serverless connector solution,
you can securely ingest first-party data to create custom audiences in TikTok.

![Alt text](imgs/arch.PNG?raw=true "Architecture")


1.	TikTok access token and advertiser_id is securely updated in **AWS Secrets Manager**
2.	Custom Audience data is uploaded in the **Amazon S3 Bucket’s** designated prefix (<S3 Bucket>/tiktok/<audiencename>/<format>/custom_auidences.csv ) in any of the following tiktok SHA256 supported format. Amazon S3 bucket is encrypted using AWS Key Management Service.
*	EMAIL_SHA256
*	PHONE_SHA256
*	IDFA_SHA256
*	GAID_SHA256
*	FIRST_SHA256
3.	**Amazon EvenBridge** routes the **Amazon S3 object** event to **Amazon SQS** enabling support for API retry, replay, and throttling.
4.	**Amazon SQS** queue event triggers TikTok Audience **Activation AWS Lambda function**.
5.	The Audience Activation lambda function retrieves the access token and advertiser_id from AWS Secrets Manager and Uploads the target custom audience to TikTok Ads. If uploaded audience is already present Activation lambda function append the audiences to current audience.
6.	TikTok Ads Direct Advertisers and Agencies or companies leverage this custom audience data as First party Audience Targeting.


## Manual Prerequisites

1.	Setup TikTok API for Business Developers by following documentation [here](https://ads.tiktok.com/marketing_api/docs?id=1735713609895937). 
2.	You need to get A long-term access token (with Audience Management Permission of scope) and advertiser_id by following the TikTok Authentication API documentation [here](https://ads.tiktok.com/marketing_api/docs?id=1738373164380162). 


## Deploying with CDK

The project code uses the Python version of the AWS CDK ([Cloud Development Kit](https://aws.amazon.com/cdk/)). To execute the project code, please ensure that you have fulfilled the [AWS CDK Prerequisites for Python](https://docs.aws.amazon.com/cdk/latest/guide/work-with-cdk-python.html).

The project code requires that the AWS account is [bootstrapped](https://docs.aws.amazon.com/de_de/cdk/latest/guide/bootstrapping.html) in order to allow the deployment of the CDK stack.


## CDK Deployment
```
# navigate to project directory
cd activation-connector-tiktok-ads

# install and activate a Python Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# install dependant libraries
python -m pip install -r requirements.txt

```

## Setup Tiktok Credentials

Update the Tiktok credentials in Secret Manager .
1. Secret **tiktok_activation_credentials**is created as part of CDK deployment. Go to the Secrets Manager Console and select  **tiktok_activation_credentials**

![Alt text](imgs/sm_1.PNG?raw=true "Secret manager ")

2. Click on Retrieve secret value
![Alt text](imgs/sm_2.PNG?raw=true "Secret manager retrive secret value")

3.  Add **ACCESS_TOKEN** and **ADVERTISER_ID** Keys and corresponding Secret values retrived from TikTok Authentication API [here](https://ads.tiktok.com/marketing_api/docs?id=1738373164380162)

![Alt text](imgs/sm_3.PNG?raw=true "Secret manager add ACCESS_TOKEN and ADVERTISER_ID ")



## Update cdk.context.json Parameter

Select a name for the S3 Bucket   `tiktok_data_bucket_name`


```
{
    "tiktok_data_bucket_name": "rajeabh-connector-data-tiktok-001"
}

```

## Execute the CDK bootstrap and deploy the application

```
cdk bootstrap 

```
Upon successful completion of cdk bootstrap, the project is ready to be deployed
```
cdk deploy

```

#  S3 Bucket Structure

Targeted Custom audience segment data needs to be normalized and hashed in SHA256 format and uploaded in Amazon S3 bucket. Amazon S3 bucket and Prefix should be in a format S3bucket/tiktok/<audience-segment-name>/<format-type>/custom_audiences.csv
where

* 	“audience-segment-name” matches with the name of the audience in TikTok Ads Manager.
*	“format-type” matches with any of the following TikTok SHA256 supported format.  
    *	email_sha256 
    *	phone_sha256
    *	idfa_sha256
    *	gaid_sha256
    *	first_sha256

Note that, format-type is NOT case sensitive for example you can give prefix name “email_sha256” or “EMAIL_SHA256” for uploading Custom Audiences segment emails encrypted with SHA256 format. 




```
S3bucket/tiktok/<custom-audience-name>/<format-type>/custom_audiences_data.csv


```
![Alt text](imgs/s3_tiktok.PNG?raw=true "Data Bucket Structure")



# TikTok Custom Audiences Schema
TikTok API for Business supports custom audience upload in following SHA256 encrypted formats.

*	EMAIL_SHA256
*	PHONE_SHA256
*	IDFA_SHA256
*	GAID_SHA256
*	FIRST_SHA256


Refer TikTok API for Business for all supported types for [Custom File Upload](https://ads.tiktok.com/marketing_api/docs?id=1739566528222210).



```
Example : PHONE_SHA256
3d562b4ba5680ddba530ca888ec699e921b74fcbf5b89e34868d2c9afcd82fb9

EMAIL_SHA256 : Email hased in SHA256 format
fd911bd8cac2e603a80efafca2210b7a917c97410f0c29d9f2bfb99867e5a589


```
**IMPORTANT! Protect your audience data! Don't upload unencrypted data.**

# Testing 
1.	Copy test custom audiences file from GitHub **/test/tiktok/test_foodies_phone_sha256_audience.csv**
TO **S3Bucket/tiktok/ foodies-custom-audience/phone_sha256/ test_foodies_phone_sha256_audience.csv**
2.	Verify Custom audience ‘foodies-custom-audience’ is created TikTok Ads Manager 
3.	Verify Custom file is uploaded for audience ‘foodies-custom-audience’ in TikTok Ads Manager.
Note that, if you upload audience with existing custom audience name, Audience data will be **Appended** to existing custom audience. 

![Alt text](imgs/tiktok_ca.PNG?raw=true "TikTok Custom Audiences ")




# Cleanup

When you’re finished experimenting with this solution, clean up your resources by running the command:

```
cdk destroy

```

This command deletes resources deploying through the solution. S3 buckets containing the call recordings and CloudWatch log groups are retained after the stack is deleted.

# Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

# License
This library is licensed under the MIT-0 License. See the LICENSE file.

# Terms and Conditions

Any custom audience that is activated through activation connector must adhere to TikTok’s Custom Audience terms, including verifying that data you share with TikTok does not include information about children, sensitive health or financial information, other categories of sensitive information.

For full details on TikTok's Custom Audience terms please review:
https://ads.tiktok.com/i18n/official/policy/custom-audience-terms




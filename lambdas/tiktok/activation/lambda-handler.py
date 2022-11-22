
import boto3
import json
import os
import logging
from botocore.exceptions import ClientError
from botocore.client import Config
import json
import requests
import urllib.parse
from datetime import datetime, timedelta
import requests
from six import string_types
from six.moves.urllib.parse import urlencode, urlunparse  # noqa
import botocore
import hashlib

logger = logging.getLogger()
logger.setLevel(logging.INFO)

tiktok_activation_credentials = os.environ['CRED_SECRET_NAME']


def get_tiktok_credentials(secret_name):
    """Get the TikTok credentials from Secret Manager"""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(
        SecretId=tiktok_activation_credentials)
    tiktok_credentials = json.loads(response['SecretString'])
    return tiktok_credentials


def update_tiktok_credentials(ACCESS_TOKEN, ADVERTISER_ID):
    """Update TikTok credentials in SecretManager"""
    tiktok_credentials = dict()
    tiktok_credentials['ACCESS_TOKEN'] = ACCESS_TOKEN
    tiktok_credentials['ADVERTISER_ID'] = ADVERTISER_ID
    client = boto3.client('secretsmanager')
    response = client.put_secret_value(
        SecretId=tiktok_activation_credentials,
        SecretString=json.dumps(tiktok_credentials)
    )
    return response


def build_url(path, query=""):
    """
    Build request URL
    :param path: Request path
    :param query: Querystring
    :return: Request URL
    """
    scheme, netloc = "https", "business-api.tiktok.com"
    return urlunparse((scheme, netloc, path, "", query, ""))


def get_custom_audience_data(bucket_name, file_key, file_name):
    """get custom auidence data from S3"""
    s3_resource = boto3.resource('s3')
    s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))
    FILE_FULL_PATH = "/tmp/{}".format(file_name)
    files = dict()
    file_signature = None
    try:
        s3_resource.Bucket(bucket_name).download_file(file_key, FILE_FULL_PATH)
        files["file"] = open(FILE_FULL_PATH, "rb")
        file_signature = hashlib.md5(
            open(FILE_FULL_PATH, 'rb').read()).hexdigest()

    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            logger.error("The object {} does not exist.".format(file_name))
        else:
            raise
    return files, file_signature


def upload_custom_audience_data(bucket_name, file_key, file_name, calculate_type):
    """upload auidence data and generate file_paths"""
    path = "/open_api/v1.3/dmp/custom_audience/file/upload/"
    url = build_url(path)
    tiktok_credentials = get_tiktok_credentials(tiktok_activation_credentials)
    json_args = {}
    files, file_signature = get_custom_audience_data(
        bucket_name, file_key, file_name)
    json_args["advertiser_id"] = tiktok_credentials["ADVERTISER_ID"]
    json_args["file_signature"] = str(file_signature.strip())
    json_args["calculate_type"] = calculate_type
    headers = {
        "Access-Token": tiktok_credentials["ACCESS_TOKEN"]
    }
    resp = requests.post(url, headers=headers, data=json_args, files=files)
    return resp.json()


def create_custom_audience_data(custom_audience_name, file_path, calculate_type):
    """create auidence data from previously uploaded file on file_path"""
    path = "/open_api/v1.3/dmp/custom_audience/create/"
    url = build_url(path)
    tiktok_credentials = get_tiktok_credentials(tiktok_activation_credentials)
    json_args = dict()
    file_paths = []
    file_paths.append(file_path)
    json_args["advertiser_id"] = tiktok_credentials["ADVERTISER_ID"]
    json_args["file_paths"] = file_paths
    json_args["custom_audience_name"] = custom_audience_name
    json_args["calculate_type"] = calculate_type
    headers = {
        "Content-Type": "application/json",
        "Access-Token": tiktok_credentials["ACCESS_TOKEN"]
    }
    resp = requests.post(url, headers=headers, json=json_args)
    return resp.json()


def update_custom_audience_data(custom_audience_id, file_path):
    """Append the auidence data from uploaded file on file_path for custom_auidence_id"""
    path = "/open_api/v1.3/dmp/custom_audience/update/"
    url = build_url(path)
    tiktok_credentials = get_tiktok_credentials(tiktok_activation_credentials)
    json_args = dict()
    file_paths = []
    file_paths.append(file_path)
    json_args["action"] = "APPEND"
    json_args["advertiser_id"] = tiktok_credentials["ADVERTISER_ID"]
    json_args["file_paths"] = file_paths
    json_args["custom_audience_id"] = custom_audience_id
    headers = {
        "Content-Type": "application/json",
        "Access-Token": tiktok_credentials["ACCESS_TOKEN"]
    }
    resp = requests.post(url, headers=headers, json=json_args)
    return resp.json()


def get_custom_auidence_obj(audience_list, custom_audience_name):
    """
    search audience_list and check custom audience is present
    :return: None if there is no custom audience found with name provided
    """
    audience_obj = None
    for obj in audience_list:
        if obj["name"] == custom_audience_name:
            audience_obj = obj
            break
    return audience_obj


def check_custom_audience_exist(custom_audience_name):
    """
    checks custom audience already exists
    :returns: None if there is no custom audience
    """
    PATH = "/open_api/v1.3/dmp/custom_audience/list/"
    tiktok_credentials = get_tiktok_credentials(tiktok_activation_credentials)
    ACCESS_TOKEN = tiktok_credentials["ACCESS_TOKEN"]
    advertiser_id = tiktok_credentials["ADVERTISER_ID"]
    page = 1
    page_size = 100
    total_page = 2
    rsp = None
    audience_obj = None
    # Pagination loop
    while (total_page > page and audience_obj is None):
        query_string = "advertiser_id={}&page={}&page_size={}".format(
            advertiser_id, page, page_size)
        url = build_url(PATH, query_string)
        headers = {
            "Access-Token": ACCESS_TOKEN,
        }
        rsp = requests.get(url, headers=headers)
        rsp_json = rsp.json()
        if "data" in rsp_json.keys():
            audience_obj = get_custom_auidence_obj(
                rsp_json["data"]["list"], custom_audience_name)
            total_page = rsp_json["data"]["page_info"]["total_page"]
        else:
            audience_obj = None
        page = page+1
    return audience_obj


def get_upload_audience_info(key):
    try:
        segment_name_prefix, file_name = os.path.split(key)
        segment_name_prefix = segment_name_prefix.split("/")
        calculate_type = get_calculate_type(str(segment_name_prefix[2]))
        custom_audience_name = str(segment_name_prefix[1])
        return file_name, calculate_type, custom_audience_name
    except IndexError:
        raise ValueError(
            "ERROR : S3 bucket structure is not in correct format : Please create a bucket structure in format <S3 Bucket>/tiktok/<audiencename>/<calculate_type>/<customaudiencefile.csv>")


def get_calculate_type(calculate_type):
    calculate_types = os.environ['SUPPORTED_CALCULATE_TYPES'].split(",")
    if calculate_type.upper() in calculate_types:
        return calculate_type.upper()
    else:
        error_message = "ERROR : calculate type {} is not in supported format {}".format(
            calculate_type, calculate_types)
        raise ValueError(error_message)


def clean_up(file_name):
    """cleanup temporary file """
    FILE_FULL_PATH = "/tmp/{}".format(file_name)
    if os.path.exists(FILE_FULL_PATH):
        os.remove(FILE_FULL_PATH)


def lambda_handler(event, context):
    resp = None
    __status_code = 200
    __message = ""
    __error_code = 400
    logger.info(event['Records'][0]['body'])
    try:
        bucket_name = json.loads(event['Records'][0]['body'])[
            'detail']['bucket']['name']
        key = urllib.parse.unquote_plus(json.loads(event['Records'][0]['body'])[
                                        'detail']['object']['key'], encoding='utf-8')
        logger.info("Key--> {}".format(key))
        file_name, calculate_type, custom_audience_name = get_upload_audience_info(key)
        logger.info("file_name--> {} calculate_type -->{} custom_audience_name --> {} ".format(file_name, calculate_type, custom_audience_name))
        # Step 1 :Upload custom audience data and get file_path.
        # file_path is required in both new and update case
        resp = upload_custom_audience_data(
            bucket_name, key, file_name, calculate_type)
        if resp['code'] == 0:
            file_path = resp["data"]["file_path"]
            # Step 2 : Check Custom audience is already present
            custom_audience_data = check_custom_audience_exist(
                custom_audience_name)
            if custom_audience_data:
                # Step 2-A : Custom audience is already present . Update the audience
                resp = update_custom_audience_data(
                    custom_audience_data["audience_id"], file_path)
                __message = "Custom Audience {} is succesfully updated in TikTok Ads!".format(
                    custom_audience_name)
            else:
                # Step 2-B : Create new audience.
                resp = create_custom_audience_data(
                    custom_audience_name, file_path, calculate_type)
                __message = "Custom Audience {} is succesfully created to TikTok Ads!".format(
                    custom_audience_name)
        # Step 3 :Clean up. Delete temporary files
        clean_up(file_name)
        if resp:
            if resp['code'] != 0:
                __message = "ERROR in uploading Custom Audience {} to TikTok Ads. ERROR-->{}".format(
                    custom_audience_name, resp['message'])
                __status_code = resp['code']

        else:
            __message = "ERROR in uploading Custom Audience {} to TikTok Ads.".format(
                custom_audience_name)
            __status_code = __error_code
    except ValueError as err:
        __message = err
        __status_code = __error_code
    except Exception as e:
        __message = "ERROR in uploading Custom Audienceto TikTok Ads. ERROR --> {}".format(
            e)
        __status_code = __error_code
    __message = str(__message)
    logger.info("status code {}".format(__status_code))
    # check statau code and log error or info message
    if __status_code != 200 and  __status_code != 0:
        logger.error(__message)
    else:
        logger.info(__message)
    return {
        'statusCode': __status_code,
        'body': json.dumps(__message)
    }

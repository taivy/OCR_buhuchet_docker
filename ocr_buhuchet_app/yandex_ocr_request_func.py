#!/bin/sh

import base64
import requests
import json
import os


def get_yandex_cloud_ocr_response(image_data):
    image_64_encode = base64.urlsafe_b64encode(image_data)
    image_64_encode = image_64_encode.decode('utf-8')

    url = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
    json_request = {
            "yandexPassportOauthToken": os.environ.get('OAUTH_TOKEN')
            }
    resp = requests.post(url, json=json_request)
    IAM_TOKEN = json.loads(resp.text)['iamToken']

    json_request = {
            "Authorization": "Bearer %s" % IAM_TOKEN,
            "folderId": os.environ.get('FOLDER_ID'),
            "analyze_specs": [{
                "content": image_64_encode,
                "features": [{
                    "type": "TEXT_DETECTION",
                    "text_detection_config": {
                        "language_codes": ["en", "ru"]
                }
            }]
        }]
    }
    
    headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % IAM_TOKEN
            }
    
    url = 'https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze'

    resp = requests.post(url, headers=headers, json=json_request)
        
    return resp.text

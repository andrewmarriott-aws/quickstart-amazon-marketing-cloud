# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


#!/usr/bin/env python3
# Author: Joshua Witt jwittaws@amazon.com
# Description:
#This Lambda function pushes changes to the customer config table to a SNS topic so that they can be consumed by other microservices

import boto3
import json
import os
import logging
from aws_lambda_powertools import Logger
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

logger = Logger(service="WorkFlowManagement", level="INFO")

def deserializeDyanmoDBItem(item):
    return {k: TypeDeserializer().deserialize(value=v) for k, v in item.items()}

def pushToSNSTopic(snsTopicArn, subject, message):
    client = boto3.client('sns')
    response = client.publish(
        TargetArn=snsTopicArn, 
        Message=json.dumps(message),
        Subject=subject[:100],
         MessageStructure='string',
         MessageGroupId='TenantConfig'
    )
    return(response)

    
def lambda_handler(event, context):
    logger.info('event: {}'.format(event))
    PushToSNSTopicResponses = []
    for record in event['Records']:
        logger.info('dynamoDB Record: {}'.format(record))
        dynamodbTable = record['eventSourceARN'].split('/')[1]
        snsTopicArn = os.environ['SNS_TOPIC_ARN']
        PushToSNSTopicResponse = pushToSNSTopic(snsTopicArn, ' Record {} for table {}'.format(record['eventName'],dynamodbTable), record )
        PushToSNSTopicResponses.append(PushToSNSTopicResponse.copy())
        logger.info('Push To SNS Topic {} Response {}'.format(snsTopicArn, PushToSNSTopicResponse))
    return (PushToSNSTopicResponses)


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


import boto3
import json


def invoke_workflow(workflow, ATS_TEAM_NAME, ENV):
    client = boto3.client('lambda')
    item = workflow

    payload = {
        'customerId': item['customerId'],
        'payload': item['Input']['payload']
    }

    response = client.invoke(
        FunctionName=f'wfm-{ATS_TEAM_NAME}-ExecutionQueueProducer-{ENV}',
        InvocationType='Event',
        Payload=json.dumps(payload)
    )
    return response

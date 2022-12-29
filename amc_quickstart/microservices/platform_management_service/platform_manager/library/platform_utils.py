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
from boto3.dynamodb.types import TypeDeserializer


class PlatformUtilities():

    @staticmethod
    ## DynamoDB serialzation
    def _deserializeDyanmoDBItem(item):
        return {k: TypeDeserializer().deserialize(value=v) for k, v in item.items()}

    @staticmethod
    ## DynamoDB scan with pagination
    def _dump_table(table_name, dynamodb_client_rd):
        results = []
        last_evaluated_key = None
        while True:
            if last_evaluated_key:
                response = dynamodb_client_rd.scan(
                    TableName=table_name,
                    ExclusiveStartKey=last_evaluated_key
                )
            else: 
                response = dynamodb_client_rd.scan(TableName=table_name)
            last_evaluated_key = response.get('LastEvaluatedKey')
            
            results.extend(response['Items'])
            
            if not last_evaluated_key:
                break
        return results

    @staticmethod
    ## Retrieve defaultPayload parameters for a single workflow
    def _get_workflow_default_parameters(workflow_table_name: str, workflowId: str, customerId: str, parameters: set):
        print(f'Using default payload for: {parameters}\n')
        dynamodb_client_rd= boto3.client('dynamodb')

        try:
            response = dynamodb_client_rd.get_item(
                TableName=workflow_table_name,
                Key = {
                    'customerId': {'S': customerId},
                    'workflowId': {'S': workflowId}
                }
            )
            if 'Item' not in response:
                print('ERROR: customerId and/or workflowId not found\n')
                return False

            default_parameters = {}
            for param in parameters:
                try:
                    item = response['Item']['defaultPayload']['M'][param]
                    val = list(item.values())[0]
                    default_parameters[param] = val
                except Exception as e:
                    print(f'ERROR: No default value set for {e} \nSet default value in the AMCWorkflows table or invoke with payload\n')
                    return False
            return default_parameters
        
        except Exception as e:
            print(e)
            return False

    @staticmethod
    # Retrieve wfm-CustomerConfig details for a single customer
    def _get_customer_config(customer_table_name: str, customerId: str):
        dynamodb_client_rd= boto3.client('dynamodb')
    
        try:
            response = dynamodb_client_rd.get_item(
                TableName=customer_table_name,
                Key = {
                    'customerId': {'S': customerId},
                }
            )
            
            if 'Item' not in response:
                print('ERROR: customerId not found\n')
                return False
            
            current_config = response['Item']
            return current_config
            
        except Exception as e:
            print(e)
            return False

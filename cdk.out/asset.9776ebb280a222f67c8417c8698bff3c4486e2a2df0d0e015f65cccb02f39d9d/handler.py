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
import os
from aws_lambda_powertools import Logger
from wfm import wfm_utils

logger = Logger(service="WorkFlowManagement", level="INFO")
wfmutils = wfm_utils.Utils(logger)

sqs = boto3.client('sqs')
ssm = boto3.client('ssm')
ddb = boto3.client('dynamodb')

from wfm import wfm_utils

wfmutils = wfm_utils.Utils(logger)


def handle_updated_item(item, event_name, configs, workflows_table, workflow_schedule_table,
                        cloudwatch_rule_name_prefix):

    # log the even type and the item received
    logger.info('event: {} item {} '.format(event_name, item))

    # get the workflow endemic type from the workflow library record
    workflow_endemic_type = ''
    if 'endemicType' in item:
        workflow_endemic_type = item['endemicType']

    # get the customer prefix from the workflow library record
    workflow_customer_prefix = ''
    if 'customerPrefix' in item:
        workflow_customer_prefix = item['customerPrefix']

    for customerId in configs:
        # set the update settings to false by default
        enable_workflow_library_updates = False
        enable_workflow_library_new_content = False
        enable_workflow_library_schedule_creation = False

        # Load the update settings from the customer record if they exist:
        if "enableWorkflowLibraryNewContent" in configs[customerId]['AMC']['WFM']:
            enable_workflow_library_new_content = configs[customerId]['AMC']['WFM']["enableWorkflowLibraryNewContent"]

        if "enableWorkflowLibraryUpdates" in configs[customerId]['AMC']['WFM']:
            enable_workflow_library_updates = configs[customerId]['AMC']['WFM']["enableWorkflowLibraryUpdates"]

        if "enableWorkflowLibraryScheduleCreation" in configs[customerId]['AMC']['WFM']:
            enable_workflow_library_schedule_creation = configs[customerId]['AMC']['WFM'][
                "enableWorkflowLibraryScheduleCreation"]

        # Set the default value for the customer endemic type
        customer_endemic_type = ''

        if "endemicType" in configs[customerId]:
            customer_endemic_type = configs[customerId]["endemicType"]

        logger.info('workflow endemic type {} customer {} endemic type {}'.format(workflow_endemic_type, customerId,
                                                                                  customer_endemic_type))

        # if the endemic type is specified in the workflow and does not match the customer record then skip updating the record for the customer
        if workflow_endemic_type != '' and workflow_endemic_type != customer_endemic_type:
            continue

        # Set the default value for the customer prefix
        customer_customer_prefix = ''

        if "customerPrefix" in configs[customerId]:
            customer_customer_prefix = configs[customerId]["customerPrefix"]

        logger.info(
            'workflow customerPrefix  {} customer {} customerPrefix {}'.format(workflow_customer_prefix, customerId,
                                                                               customer_customer_prefix))

        # if the customer prefix is specified in the workflow and does not match the customer record then skip updating the record for the customer
        if workflow_customer_prefix != '' and workflow_customer_prefix != customer_customer_prefix:
            continue

        workflow_item_to_update = item.copy()
        workflow_item_to_update['customerId'] = customerId

        workflow_exists = wfmutils.dynamodb_check_if_item_exists(workflows_table, workflow_item_to_update)

        # if the customer config does not allow updates check to see if the workflow exists, if it does then skip
        if not enable_workflow_library_updates and workflow_exists:
            continue
        # if the customer config does not allow new items and the workflow does not already exist then skip
        if not enable_workflow_library_new_content and not workflow_exists:
            continue

        workflow_item_to_update.pop('schedule', None)
        wfmutils.dynamodb_put_item(workflows_table, workflow_item_to_update)

        if 'schedule' in item:
            schedule_item_to_update = item['schedule'].copy()
            # copy the workflowid into the payload
            schedule_item_to_update['customerId'] = customerId
        
            # only add the cloudformation rule to the list of items to be updated if it does not already exist
            if enable_workflow_library_schedule_creation and not wfmutils.dynamodb_check_if_item_exists(
                    workflow_schedule_table, schedule_item_to_update):
                wfmutils.dynamodb_put_item(workflow_schedule_table, schedule_item_to_update)


def handle_deleted_item(item, event_name, configs, workflows_table, workflow_schedule_table,
                        cloudwatch_rule_name_prefix):

    # log the event type and the item received
    logger.info('event: {} item {} '.format(event_name, item))

    for customerId in configs:
        # set the update settings to false by default
        enable_workflow_library_removal = False
        enable_workflow_library_schedule_removal = False

        # Load the update settings from the customer record if they exist:
        if "enableWorkflowLibraryRemoval" in configs[customerId]['AMC']['WFM']:
            enable_workflow_library_removal = configs[customerId]['AMC']['WFM']["enableWorkflowLibraryRemoval"]

        if "enableWorkflowLibraryScheduleRemoval" in configs[customerId]['AMC']['WFM']:
            enable_workflow_library_schedule_removal = configs[customerId]['AMC']['WFM'][
                "enableWorkflowLibraryScheduleRemoval"]

        workflow_item_to_delete = item.copy()
        workflow_item_to_delete['customerId'] = customerId

        workflow_exists = wfmutils.dynamodb_check_if_item_exists(workflows_table, workflow_item_to_delete)

        # only remove the worklow record if the customer config allows workflow removal and the record exists
        if enable_workflow_library_removal and workflow_exists:
            wfmutils.dynamodb_delete_item(workflows_table, workflow_item_to_delete, True)

        #remove the schedule if it existed for the workflow library record
        schedule_item_to_delete = item['schedule'].copy()
        schedule_item_to_delete['customerId'] = customerId
        schedule_exists = wfmutils.dynamodb_check_if_item_exists(workflow_schedule_table, schedule_item_to_delete)
        # only add the cloudformation rule to the list of items to be updated if it does not already exist
        if enable_workflow_library_schedule_removal and schedule_exists:
            wfmutils.dynamodb_delete_item(workflow_schedule_table, schedule_item_to_delete, False)


def lambda_handler(event, context):
    logger.info('event: {}'.format(event))
    workflows_table = os.environ['WORKFLOWS_TABLE_NAME']
    workflow_schedule_table = os.environ['WORKFLOW_SCHEDULE_TABLE']
    cloudwatch_rule_name_prefix = os.environ['CLOUDWATCH_RULE_NAME_PREFIX']
    workflow_library_table = os.environ['WORKFLOW_LIBRARY_DYNAMODB_TABLE']

    # check to see if the trigger is being invoked for a new customer that needs to have the default workflows deployed
    if 'customerId' in event and 'deployForNewCustomer' in event and event['deployForNewCustomer']:
        # get the customer config record for the specific customer
        customer_config = wfmutils.dynamodb_get_customer_config_records(os.environ['CUSTOMERS_DYNAMODB_TABLE'],
                                                                        event['customerId'])
        # get the entire workflow library record set
        dynamodb_records = wfmutils.dynamodb_get_all_records(workflow_library_table)
        for workflow_library_record in dynamodb_records:
            logger.info(workflow_library_record)
            # treat each workflow records with auto deploy as if it were a newly inserted record for this customerId
            handle_updated_item(workflow_library_record, 'INSERT', customer_config, workflows_table,
                                    workflow_schedule_table,
                                    cloudwatch_rule_name_prefix)
        return

    configs = wfmutils.dynamodb_get_customer_config_records(os.environ['CUSTOMERS_DYNAMODB_TABLE'])
    response = {}
    for record in event['Records']:

        if 'dynamodb' in record and 'NewImage' in record['dynamodb']:
            new_record = wfmutils.deseralize_dynamodb_item(record['dynamodb']['NewImage'])

        if 'dynamodb' in record and 'OldImage' in record['dynamodb']:
            old_record = wfmutils.deseralize_dynamodb_item(record['dynamodb']['OldImage'])

        if record['eventName'] in ['INSERT', 'MODIFY']:
            handle_updated_item(new_record, record['eventName'], configs, workflows_table, workflow_schedule_table,
                                cloudwatch_rule_name_prefix)

        if record['eventName'] in ['REMOVE']:
            handle_deleted_item(old_record, record['eventName'], configs, workflows_table, workflow_schedule_table,
                                cloudwatch_rule_name_prefix)

    return response

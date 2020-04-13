import boto3
import os
import json
import requests
import sys
from dotenv import load_dotenv

def getSSMParameter(nameSSMParameter):
    print("Start: Get SSMParameter")
    try:    
        response = client_ssm.get_parameter(Name=nameSSMParameter, WithDecryption=True)
        print("Finish: Get SSMParameter")
        return (response['Parameter']['Value'])
    except Exception as e: 
        print(e)
        print ("Error getting SSMParameter")
        sys.exit(1)
def updateSSMParameter(nameSSMParameter,currentSSMParameter,newSSMParameter):
    print("Start: Update SSMParameter")
    try:
        currentValues = json.loads(currentSSMParameter)
        currentValues['pd_token'] = newSSMParameter['access_token']
        currentValues['pd_refresh_token'] = newSSMParameter['refresh_token']
        newValues = json.dumps(currentValues)
        response = client_ssm.put_parameter(Name=os.environ["SSM_PARAMETERS"], Type='SecureString', Value=str(newValues), Overwrite=True)
        print("Finish: Update SSMParameter")
        return (response)
    except Exception as e: 
        print(e)
        print ("Error updating SSMParameter")
        sys.exit(1)

def refreshToken(valueSSMParameter):
    print("Start: Refresh Access Token")
    try:
        auth_parameters = json.loads(valueSSMParameter)
        params = {'grant_type':'refresh_token',
                    'client_id':auth_parameters['client_id'],
                    'client_secret':auth_parameters['client_secret'],
                    'refresh_token':auth_parameters['pd_refresh_token']
                    }
        print("Start: External API connection")
        refreshRequest = requests.post(url=os.environ["URL_AUTH"], params=params)
        print("Start connection")
        response = refreshRequest.json()
        if refreshRequest.status_code == 200:
            print ("Successful connection. HTTP STATUS: "+str(refreshRequest.status_code))
        else:
            print("Some error occurs in connection. HTTP STATUS: "+str(refreshRequest.status_code))
            raise
        print("Finish: Refresh Access Token")
        return (response)
    except Exception as e: 
        print(e)
        print ("Error refreshing Access Token ")
        sys.exit(1)

def lambda_handler(event, lambda_context):
    print ("Start Lambda")
    currentSSMParameter = getSSMParameter(os.environ["SSM_PARAMETERS"])
    newSSMParameter = refreshToken(currentSSMParameter)
    updateToken = updateSSMParameter(os.environ["SSM_PARAMETERS"],currentSSMParameter,newSSMParameter)
    print(updateToken)
    print ("Finish Lambda")

if 'OS' in os.environ:
    load_dotenv()
    session = boto3.Session(profile_name='dev', region_name='us-east-1')
    client_ssm = session.client('ssm')
    event="1"
    lambda_context=""
    lambda_handler(event, lambda_context)
else:
    client_ssm = boto3.client('ssm')
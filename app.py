import boto3
import os
import json
import requests
import sys
from dotenv import load_dotenv
from icalendar import Calendar, Event
import recurring_ical_events
from datetime import date, datetime, timedelta


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
def getAnalyst(valueSSMParameter,analystEmail):
    print("Start: Get Analyst Info")
    try:
        auth_parameters = json.loads(valueSSMParameter)
        headers = {'authorization':"Bearer "+auth_parameters['pd_token'],
                    'accept':"application/vnd.pagerduty+json;version=2"
                    }
        params = {'query':analystEmail}
        print("Start: External API connection")
        responseApi = requests.get(url=os.environ["URL_API"]+"/users", headers=headers , params=params)
        if responseApi.status_code == 200:
            print ("Successful connection. HTTP STATUS: "+str(responseApi.status_code))
        else:
            print("Some error occurs in connection. HTTP STATUS: "+str(responseApi.status_code))
            raise
        userInfo = responseApi.json()
        userID = str(userInfo['users'][0]['id'])
        userName = str(userInfo['users'][0]['name'])
        userSelf = str(userInfo['users'][0]['self'])
        userHtml = str(userInfo['users'][0]['html_url'])
        teamID = str(userInfo['users'][0]['teams'][0]['id'])
        response = {'userID':userID,'userName':userName,'userSelf':userSelf,'userHtml':userHtml,'teamID':teamID}
        print ("UserID: "+response['userID'])
        print ("TeamID: "+response['teamID'])
        print("Finish: Get Analyst Info")
        return (response)
    except Exception as e: 
        print(e)
        print ("Error getting Analyst Info")
        sys.exit(1)
def getEscalationID(valueSSMParameter,oncallAnalyst):
    print("Start: Get Escalation Info")
    try:
        auth_parameters = json.loads(valueSSMParameter)
        headers = {'authorization':"Bearer "+auth_parameters['pd_token'],
                    'accept':"application/vnd.pagerduty+json;version=2"
                    }
        params = {'team_ids[]':oncallAnalyst['teamID']}
        print("Start: External API connection")
        responseApi = requests.get(url=os.environ["URL_API"]+"/escalation_policies", headers=headers , params=params)
        if responseApi.status_code == 200:
            print("Successful connection. HTTP STATUS: "+str(responseApi.status_code))
        else:
            print("Some error occurs in connection. HTTP STATUS: "+str(responseApi.status_code))
            raise
        escalationInfo = responseApi.json()
        escalationID = escalationInfo['escalation_policies'][0]['id']
        escalationRules = escalationInfo['escalation_policies'][0]['escalation_rules']
        if oncallAnalyst['userID'] == escalationRules[0]['targets'][0]['id']:
            print("The analyst is already on-call.")
            print("Stop: Get Escalation Info")
            return False
        else:
            print("The on-call escalation need update.")
            print("Stop: Get Escalation Info")
            return {'id':escalationID,'rules':escalationRules}
    except Exception as e:
        print(e)
        print ("Error getting Escalation Info")
        sys.exit(1)
def updateEscalation(valueSSMParameter,oncallAnalyst,escalationInfo):
    print("Start: Escalation Update")
    try:
        auth_parameters = json.loads(valueSSMParameter)
        headers = {'authorization':"Bearer "+auth_parameters['pd_token'],
                    'accept':"application/vnd.pagerduty+json;version=2",
                    'content-type':"application/json"
                    }
        body = json.dumps(
                            {
                                "escalation_policy": {
                                    "type": "escalation_policy",
                                    "id": escalationInfo['id'],
                                    "escalation_rules": [
                                        {
                                            "id": escalationInfo['rules']['0']['id'],
                                            "escalation_delay_in_minutes": escalationInfo['rules'][0]['escalation_delay_in_minutes'],
                                            "targets": [
                                                {
                                                    "id": oncallAnalyst['userID'],
                                                    "type": "user_reference"
                                                }
                                            ]
                                        }
                                    ]
                                }
                            }
                        )
        print("Start: External API connection")
        responseApi = requests.put(url=os.environ["URL_API"]+"/escalation_policies/PJWAEZY", headers=headers , data=body)
        if responseApi.status_code == 200:
            print("Successful connection. HTTP STATUS: "+str(responseApi.status_code))
        else:
            print("Some error occurs in connection. HTTP STATUS: "+str(responseApi.status_code))
            raise
        print(responseApi.json())
 
    except Exception as e: 
        print(e)
        print ("Error updating Escalation Update")
        sys.exit(1)


def icsParser():
    #Adept this part according to your need
    print ("Start: Calendar Parser")
    icsURL=os.environ["URL_ICS"]
    print("Start Calendar connection ")
    icsCalendar = requests.get(url=icsURL)
    if icsCalendar.status_code == 200:
        print ("Successful connection. HTTP STATUS: "+str(icsCalendar.status_code))
    else:
        print("Some error occurs in connection. HTTP STATUS: "+str(icsCalendar.status_code))
    icsCalendar = Calendar.from_ical(icsCalendar.text)
    today = datetime.today()
    events = recurring_ical_events.of(icsCalendar).at(today)
    for event in events:
        #Update strech if event signature update
        if "Sobreaviso" in event["SUMMARY"]:
            print ("Today: "+str(today))
            print ("START ON-CALL: "+str(event['DTSTART'].dt))
            print ("END ON-CAL: "+str(event['DTEND'].dt))
            summary = event['SUMMARY'].splitlines()
            email = summary[2].split(" - ")
            print ("ANALYST: "+email[1])
            return (email[1])

def lambda_handler(event, lambda_context):
    print ("Start Lambda")
    currentSSMParameter = getSSMParameter(os.environ["SSM_PARAMETERS"])
    analystEmail = icsParser()
    oncallAnalyst = getAnalyst(currentSSMParameter,analystEmail)
    escalationInfo = getEscalationID(currentSSMParameter,oncallAnalyst)
    if escalationInfo is False:
        print("Not necessary update the On-Call Escalation")
    else:
        print("it will necessary update the On-Call Escalation")
        updateEscalation(currentSSMParameter,oncallAnalyst,escalationInfo)
    #newSSMParameter = refreshToken(currentSSMParameter)
    #updateToken = updateSSMParameter(os.environ["SSM_PARAMETERS"],currentSSMParameter,newSSMParameter)
    print("Finish Lambda")

if 'OS' in os.environ:
    load_dotenv()
    session = boto3.Session(profile_name='dev', region_name='us-east-1')
    client_ssm = session.client('ssm')
    event="1"
    lambda_context=""
    lambda_handler(event, lambda_context)
else:
    client_ssm = boto3.client('ssm')
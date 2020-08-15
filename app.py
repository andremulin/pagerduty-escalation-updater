import boto3
import os
import json
import requests
import sys
from dotenv import load_dotenv
from icalendar import Calendar, Event
import recurring_ical_events
from datetime import date, datetime, timedelta


def sendSlack(currentSSMParameter,mensage):
    try:
        print ("Start: Send Slack mensage")
        currentSSMParameterJson = json.loads(currentSSMParameter)
        for slack in currentSSMParameterJson['slacks']:
            sendSlack = requests.post(url=slack , headers={'content-type':'application/json'}, data=json.dumps({"text":mensage}))
        print ("Finish: Send Slack mensage")
    except Exception as e: 
        print ("Error sending Slack mensage: "+str(e))
        sys.exit(1)

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

def refreshToken(currentSSMParameter):
    print("Start: Refresh Access Token")
    try:
        auth_parameters = json.loads(currentSSMParameter)
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

def getAnalyst(currentSSMParameter,analystToday):
    print("Start: Get Analyst Info")
    try:
        auth_parameters = json.loads(currentSSMParameter)
        headers = {'authorization':"Bearer "+auth_parameters['pd_token'],
                    'accept':"application/vnd.pagerduty+json;version=2"
                    }
        params = {'query':analystToday['email']}
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
        print("Finish: Get Analyst Info")
        return (response)
    except Exception as e: 
        print(e)
        print ("Error getting Analyst Info")
        sys.exit(1)

def getEscalationID(currentSSMParameter,oncallAnalyst):
    print("Start: Get Escalation Info")
    try:
        auth_parameters = json.loads(currentSSMParameter)
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
            print("Stop: Get Escalation Info")
            return False
        else:
            print("Stop: Get Escalation Info")
            return ({'id':escalationID,'rules':escalationInfo})
    except Exception as e:
        print(e)
        print ("Error getting Escalation Info")
        sys.exit(1)

def updateEscalation(currentSSMParameter,oncallAnalyst,escalationInfo):
    print("Start: Escalation Update")
    try:
        auth_parameters = json.loads(currentSSMParameter)
        headers = {'authorization':"Bearer "+auth_parameters['pd_token'],
                    'accept':"application/vnd.pagerduty+json;version=2",
                    'content-type':"application/json"
                    }
        escalation_policy = escalationInfo['rules']['escalation_policies']
        if escalation_policy[0]:
            if 'escalation_rules' in escalation_policy[0]:
                if 'targets' in escalation_policy[0]['escalation_rules'][0]:
                    escalation_policy[0]['escalation_rules'][0]['targets'][0] = {'id':oncallAnalyst['userID'], 'type':"user_reference"}
                    body = {}
                    body = {'escalation_policy': escalation_policy[0]}
                    body = json.dumps(body)


        print("Start: External API connection")
        responseApi = requests.put(url=os.environ["URL_API"]+"/escalation_policies/"+escalationInfo['id'], headers=headers , data=body)
        if responseApi.status_code == 200:
            print("Successful connection. HTTP STATUS: "+str(responseApi.status_code))
        else:
            print("Some error occurs in connection. HTTP STATUS: "+str(responseApi.status_code))
            raise
        return(0)
 
    except Exception as e: 
        print(e)
        print ("Error updating Escalation Update")
        sys.exit(1)

def icsParser(currentSSMParameter):
    #Adept this part according to your need
    auth_parameters = json.loads(currentSSMParameter)
    print ("Start: Calendar Parser")
    icsURL=auth_parameters["url_ics"]
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
        if "Sobreaviso" in event['SUMMARY']:
            print ("Today: "+str(today))
            print ("START ON-CALL: "+str(event['DTSTART'].dt))
            print ("END ON-CAL: "+str(event['DTEND'].dt))
            summary = event['SUMMARY'].splitlines()
            email = summary[2].split(" - ")
            email = email[1].strip()
            print ("ANALYST EMAIL: "+email)
            response = {'email':email}
            return (response)

def lambda_handler(event, lambda_context):
    print ("Start Lambda")
    currentSSMParameter = getSSMParameter(os.environ["SSM_PARAMETERS"])
    analystToday = icsParser(currentSSMParameter)
    oncallAnalyst = getAnalyst(currentSSMParameter,analystToday)
    escalationInfo = getEscalationID(currentSSMParameter,oncallAnalyst)
    if escalationInfo is False:
        print("Not necessary update the On-Call Escalation")
    else:
        print("it will necessary update the On-Call Escalation")
        if updateEscalation(currentSSMParameter,oncallAnalyst,escalationInfo) == 0:
            response = "The analyst "+oncallAnalyst['userName']+" took the on-call."
            sendSlack(currentSSMParameter,response)
    if date.today().weekday() == 0:
        newSSMParameter = refreshToken(currentSSMParameter)
        updateToken = updateSSMParameter(os.environ["SSM_PARAMETERS"],currentSSMParameter,newSSMParameter)
    print("Finish Lambda")

if 'OS' in os.environ:
    print ("Env: Desktop")
    load_dotenv()
    session = boto3.Session(profile_name='dev', region_name='us-east-1')
    client_ssm = session.client('ssm')
    event="1"
    lambda_context=""
    lambda_handler(event, lambda_context)
else:
    print ("Env: Lambda")
    client_ssm = boto3.client('ssm')

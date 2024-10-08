# This sample source code is provided as a demonstration of potential solutions for 
# IDMC source control deployment pipeline and is intended for educational purposes only. 
# The code is supplied "as-is," without any warranties or guarantees, and is not officially 
# supported by Informatica. Users who utilize this code, in part or in full, 
# or create derivatives, do so at their own risk. Informatica disclaims any and 
# all liabilities resulting from its use, to the maximum extent allowed by law.

import requests
import os
import json
import time
import sys

URL = os.environ['IICS_POD_URL']
UAT_SESSION_ID = os.environ['UAT_SESSIONID']
UAT_COMMIT_HASH = os.environ['UAT_COMMIT_HASH']

HEADERS = {"Content-Type": "application/json; charset=utf-8", "INFA-SESSION-ID": UAT_SESSION_ID }
HEADERS_V2 = {"Content-Type": "application/json; charset=utf-8", "icSessionId": UAT_SESSION_ID }

BODY={ "commitHash": UAT_COMMIT_HASH}

print("Syncing the commit " + UAT_COMMIT_HASH + " to the UAT repo")

# Sync Github and UAT Org
p = requests.post(URL + "/public/core/v3/pullByCommitHash", headers = HEADERS, json=BODY)

if p.status_code != 200:
    print("Exception caught: " + p.text)
    sys.exit(99)

pull_json = p.json()
PULL_ACTION_ID = pull_json['pullActionId']
PULL_STATUS = 'IN_PROGRESS'

while PULL_STATUS == 'IN_PROGRESS':
    print("Getting pull status from Informatica")
    time.sleep(10)
    ps = requests.get(URL + '/public/core/v3/sourceControlAction/' + PULL_ACTION_ID, headers = HEADERS, json=BODY)
    pull_status_json = ps.json()
    PULL_STATUS = pull_status_json['status']['state']



if PULL_STATUS != 'SUCCESSFUL':
    print('Exception caught: Pull was not successful')
    sys.exit(99)

# Get all the objects for commit
r = requests.get(URL + "/public/core/v3/commit/" + UAT_COMMIT_HASH, headers = HEADERS)

if r.status_code != 200:
    print("Exception caught: " + r.text)
    sys.exit(99)
    
request_json = r.json()

# Only get Mapping Tasks where action is different from DELETED
r_filtered = [x for x in request_json['changes'] if x['type'] == 'MTT' and x['action'] != 'DELETED']

# This loop runs tests for each one of the mapping tasks
for x in r_filtered:
    BODY = {"@type": "job","taskId": x['appContextId'],"taskType": "MTT"}
    t = requests.post(URL + "/api/v2/job/", headers = HEADERS_V2, json = BODY )

    if t.status_code != 200:
        print("Exception caught: " + t.text)
        sys.exit(99)

    test_json = t.json()
    PARAMS = "?runId=" + str(test_json['runId'])
    #"?taskId=" + test_json['taskId']

    STATE=0
    
    while STATE == 0:
        time.sleep(60)
        a = requests.get(URL + "/api/v2/activity/activityLog" + PARAMS, headers = HEADERS_V2)
        
        activity_log = a.json()

        STATE = activity_log[0]['state']

    if STATE != 1:
        print("Mapping task: " + activity_log[0]['objectName'] + " failed. ")
        sys.exit(99)
    else:
        print("Mapping task: " + activity_log[0]['objectName'] + " completed successfully. ")

requests.post(URL + "/public/core/v3/logout", headers = HEADERS)

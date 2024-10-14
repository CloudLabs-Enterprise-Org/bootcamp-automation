from gh import client, comments
import sys
import os
import logging
import yaml
import time
import requests
from datetime import datetime

import logging

# Configure logging to write to a file
logging.basicConfig(filename='script_log.log', level=logging.DEBUG)
# Log script start
logging.info('Script started')

print("Number of arguments:", len(sys.argv))
print("Argument list:", str(sys.argv))
# Get Arguments
working_repo = 'CloudLabs-Enterprise-Org/bootcamp-automation'
issue_num = '43'
githubuser = sys.argv[1]

# Get Environment Variables
github_token = sys.argv[2] 
admin_token = sys.argv[3] 

# Setup clients
issue_ops_client = client.Client(github_token, working_repo, issue_num)
admin_client = client.Client(admin_token) 


def get_config(config_file):
    with open(config_file, "r") as stream:
        try:
            return yaml.safe_load(stream)["bootcamp-setup"]
        except yaml.YAMLError as e:
            logging.error(e)
            sys.exit(1)

def extract_issue_fields():
    try:
        issue = issue_ops_client.issue.get()
        issue_body = issue["body"]
        lines = issue_body.split("\n")
    except Exception as e:
        raise e

    bootcamp_date = datetime.now().strftime('%Y-%m-%d')
    attendee_handles = [githubuser,]
    facilitator_handles = ['cloudlabs-enterprise',]



    return bootcamp_date, attendee_handles, facilitator_handles

def build_attendees(handles):
    attendees = []
    for handle in handles:
        attendee = {
            "handle": handle,
            "id": None,
            "invited": False,
            "org_id": None,
            "org_name": None,
            "fork_errors": [],
        }
        try:
            attendee["id"] = admin_client.user.get_id(handle)
        except Exception as e:
            raise e

        attendees.append(attendee)
        print(attendees)
    return attendees



def get_organization_info(org_name):
    headers = {
        'Authorization': 'token ${admin_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    url = f'https://api.github.com/orgs/{org_name}'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        org_info = response.json()
        org_id = org_info.get('id')
        org_login = org_info.get('login')
        print(f"Organization ID: {org_id}")
        print(f"Organization login: {org_login}")
        return org_id, org_login
    else:
        print(f"Failed to fetch organization info for {org_name}: {response.status_code} - {response.text}")
        return None, None

def provision_environments(attendee_state, config, enterprise_id, bootcamp_date, facilitator_state):
    facilitator_handles = [facilitator["handle"] for facilitator in facilitator_state]
    facilitator_handles.append(config["billing-admin"])

    for attendee in attendee_state:
        try:
            handle_parts = attendee["handle"].split('-')
            last_part = handle_parts[-1]  # Selecting the last part of the split string
            org_name = config["org-prefix"] + "-" + bootcamp_date + "-" + "cloudlabs" + last_part
            if len(org_name) > 39:
                org_name = org_name[:38]

            # Create organization
            org_id, org_name = admin_client.org.create(
                enterprise_id,
                org_name,
                facilitator_handles,
                f"{config['billing-admin']}@spektrasystems.com",
            )
            
            # Fetch organization information
            org_id, org_login = get_organization_info(org_name)

            if org_id and org_login:
                attendee.update({"org_id": org_id, "org_name": org_login})
                print(attendee)
        except Exception as e:
            print(f"Error provisioning environment for {attendee['handle']}: {e}")

    return attendee_state, org_name


def fork_repo(
    attendee_state, config, facilitator_state, org_name
):
    facilitator_handles = [facilitator["handle"] for facilitator in facilitator_state]
    facilitator_handles.append(config["billing-admin"])

    # Create orgs and fork repos
    for attendee in attendee_state:
        
        for repo in config["repos-to-fork"]:
            try:
                admin_client.repo.fork(repo, org_name)
                # Make forked repos private, except for .github
                if repo.split("/")[1] != ".github":
                    forked_repo = org_name + "/" + repo.split("/")[1]
                    # Adding a sleep to avoid race condition when creating a repo and marking it private
                    time.sleep(15)
                    #admin_client.repo.visibility(forked_repo, "private")
            except Exception:
                attendee["fork_errors"].append(repo)
                pass

    return attendee_state

def main():
    # Get config
    config = get_config("config.yml")
    for key, value in config.items():
        logging.info(f"{key}: {value}")
    try:
        bootcamp_date, attendee_handles, facilitator_handles = extract_issue_fields()
        print(bootcamp_date)
        print(attendee_handles)
        print(facilitator_handles)
    except Exception as e:
        logging.error(e)
        sys.exit(1)
    #print(build_attendees)
    try:
        enterprise_id = admin_client.enterprise.get_id(config["enterprise"])
        print(enterprise_id)
    except Exception as e:
        logging.error(e)
        sys.exit(1)
    try:
        attendee_state = build_attendees(attendee_handles)
        facilitator_state = build_attendees(facilitator_handles)
        print(attendee_state)
        print(facilitator_state)
    except Exception as e:
        logging.error(e)
        sys.exit(1)

  
    attendee_state, org_name = provision_environments(
        attendee_state, config, enterprise_id, bootcamp_date, facilitator_state
    )
    print(attendee_state)

    attendee_state = fork_repo(
        attendee_state, config,  facilitator_state , org_name
    )
    print(attendee_state)

    error_count = 0
    for attendee in attendee_state:
        if org_name:
            try:
                admin_client.org.invite_member(attendee["id"], org_name)
                attendee["invited"] = True
            except Exception as e:
                logging.error(e)
                sys.exit(1)
        else:
            error_count += 1

if __name__ == "__main__":
    main()
# Log script end
logging.info('Script finished')

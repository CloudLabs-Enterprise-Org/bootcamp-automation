import requests
import logging
import gh.graphql as graphql
import time

class Repo:
    def __init__(self, client):
        self.client = client

    def fork(self, name_with_owner, org_name):
        url = f"{self.client.base_url}/repos/{name_with_owner}/forks"
        # Adding the default_branch_only parameter to the fork request
        # to avoid forking all branches of the repo and causing hang-ups
        data = {"organization": org_name, "default_branch_only": True}
        response = requests.post(url, headers=self.client.headers, json=data)
        if response.status_code == 202:
            logging.info(f"Successfully forked {name_with_owner} to {org_name}")
            return response.json()["full_name"]
        else:
            e = f"Error forking repository.  Response: {response.json()}"
            logging.error(e)
            raise Exception(e)

    def visibility(self, name_with_owner, visibility):
        url = f"{self.client.base_url}/repos/{name_with_owner}"
        data = {"visibility": visibility}
        response = requests.patch(url, headers=self.client.headers, json=data)
        if response.status_code == 200:
            logging.info(
                f"Successfully set visibility of {name_with_owner} to {visibility}"
            )
            return
        else:
            e = f"Error setting visibility of repository.  Response: {response.json()}"
            logging.error(e)
            raise Exception(e)


class Org:
    def __init__(self, client):
        self.client = client

    def create(self, enterprise_id, org_name, admin_logins, billing_email):
        variables = {
            "enterpriseId": enterprise_id,
            "login": org_name,
            "profileName": org_name,
            "adminLogins": admin_logins,
            "billingEmail": billing_email,
        }
        response = requests.post(
            self.client.graphql_url,
            headers=self.client.headers,
            json={"query": graphql.create_org, "variables": variables},
        )
        wait_time = 30
        logging.info(f"Waiting {wait_time} seconds for orgs to be created")
        time.sleep(wait_time)


    def invite_member(self, user_id, org_name):
        url = f"{self.client.base_url}/orgs/{org_name}/invitations"
        data = {"invitee_id": user_id, "role": "admin"}

        response = requests.post(url, headers=self.client.headers, json=data)
        if response.status_code == 201:
            logging.info(f"Successfully invited {user_id} to {org_name}")
            return
        else:
            e = f"Error inviting user to organization. Response: {response.json()}"
            logging.error(e)
            raise Exception(e)

    def delete(self, org_name):
        url = f"{self.client.base_url}/orgs/{org_name}"
        response = requests.delete(url, headers=self.client.headers)
        if response.status_code == 202:
            logging.info(f"Successfully deleted organization: {org_name}")
            return
        else:
            e = f"Error deleting organization: {org_name}. Response: {response.json()}"
            logging.error(e)
            raise Exception(e)


class Enterprise:
    def __init__(self, client):
        self.client = client

    def get_id(self, enterprise_slug):
        variables = {"slug": enterprise_slug}
        response = requests.post(
            self.client.graphql_url,
            headers=self.client.headers,
            json={"query": graphql.get_ent_id, "variables": variables},
        )
        if response.status_code == 200:
            id = response.json()["data"]["enterprise"]["id"]
            logging.info(f"Successfully got enterprise id: {id}")
            return id
        else:
            e = f"Error getting enterprise id: {response.json()}"
            logging.error(e)
            raise Exception(e)


class Issue:
    def __init__(self, client, working_repo=None, issue_num=None):
        self.client = client
        if working_repo:
            self.working_repo = working_repo
        if issue_num:
            self.issue_num = issue_num

    def get(self, labels=None):
        if labels:
            url = f"{self.client.base_url}/repos/{self.working_repo}/issues?labels={labels}"
        else:
            url = f"{self.client.base_url}/repos/{self.working_repo}/issues/{self.issue_num}"
        response = requests.get(url, headers=self.client.headers)
        if response.status_code == 200:
            logging.info(f"Successfully got issue: {self.issue_num}")
            return response.json()
        else:
            e = f"Error getting issue: {response.json()}"
            logging.error(e)
            raise Exception(e)

    def apply_label(self, label):
        url = f"{self.client.base_url}/repos/{self.working_repo}/issues/{self.issue_num}/labels"
        response = requests.post(url, headers=self.client.headers, json=[label])
        if response.status_code == 200:
            logging.info(
                f"Successfully applied label {label} to issue {self.issue_num}"
            )
        else:
            e = f"Error applying label {label} to issue {self.issue_num}: {response.json()}"
            logging.error(e)
            raise Exception(e)

    def remove_label(self, label):
        url = f"{self.client.base_url}/repos/{self.working_repo}/issues/{self.issue_num}/labels/{label}"
        response = requests.delete(url, headers=self.client.headers)
        if response.status_code == 200:
            logging.info(
                f"Successfully removed label {label} from issue {self.issue_num}"
            )
        else:
            e = f"Error removing label {label} from issue {self.issue_num}: {response.json()}"
            logging.error(e)
            raise Exception(e)

    def add_comment(self, comment):
        url = f"{self.client.base_url}/repos/{self.working_repo}/issues/{self.issue_num}/comments"
        response = requests.post(
            url, headers=self.client.headers, json={"body": comment}
        )
        if response.status_code == 201:
            logging.info(f"Successfully added comment to issue {self.issue_num}")
        else:
            e = f"Error adding comment to issue {self.issue_num}: {response.json()}"
            logging.error(e)
            raise Exception(e)

    def get_comments(self):
        url = f"{self.client.base_url}/repos/{self.working_repo}/issues/{self.issue_num}/comments"
        response = requests.get(url, headers=self.client.headers)
        if response.status_code == 200:
            logging.info(f"Successfully got comments for issue: {self.issue_num}")
            return response.json()
        else:
            e = f"Error getting comments for issue: {response.json()}"
            logging.error(e)
            raise Exception(e)

    def close(self):
        url = (
            f"{self.client.base_url}/repos/{self.working_repo}/issues/{self.issue_num}"
        )
        response = requests.patch(
            url, headers=self.client.headers, json={"state": "closed"}
        )
        if response.status_code == 200:
            logging.info(f"Successfully closed issue {self.issue_num}")
        else:
            e = f"Error closing issue {self.issue_num}: {response.json()}"
            logging.error(e)
            raise Exception(e)


class User:
    def __init__(self, client):
        self.client = client

    def get_id(self, username):
        url = f"{self.client.base_url}/users/{username}"
        response = requests.get(url, headers=self.client.headers)
        if response.status_code == 200:
            id = response.json()["id"]
            logging.info(f"{username} ID: {id}")
            return id
        elif response.status_code == 404:
            e = f"User {username} does not exist"
            logging.error(e)
            raise Exception(e)
        else:
            e = f"Error getting user id: {response.json()}"
            logging.error(e)
            raise Exception(e)

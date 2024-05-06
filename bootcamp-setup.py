from gh import client, comments
import sys
import os
import logging
import yaml
import time

# Get Arguments

working_repo = sys.argv[1]

issue_num = sys.argv[2]



# Get Environment Variables

github_token = os.environ.get("GITHUB_TOKEN")

admin_token = os.environ.get("ENT_ADMIN_TOKEN")

# Setup clients
issue_ops_client = client.Client(github_token, working_repo, issue_num)
admin_client = client.Client(admin_token)

logging.info("Starting bootcamp setup")
logging.info(f"Working repo: {working_repo}")
logging.info(f"Issue number: {issue_num}")


# Read config file
def get_config(config_file):
    with open(config_file, "r") as stream:
        try:
            return yaml.safe_load(stream)["bootcamp-setup"]
        except yaml.YAMLError as e:
            logging.error(e)
            sys.exit(1)


# Get bootcamp date, attendees, and facilitators from issue body
def extract_issue_fields():
    try:
        issue = issue_ops_client.issue.get()
        issue_body = issue["body"]
        lines = issue_body.split("\n")
    except Exception as e:
        raise e

    bootcamp_date = None
    attendee_handles = None
    facilitator_handles = None

    for i, line in enumerate(lines):
        if line == "### Bootcamp Date":
            bootcamp_date = lines[i + 2].strip()
        elif line == "### Attendees":
            attendee_handles = [
                attendee.strip() for attendee in lines[i + 2].split(",")
            ]
        elif line == "### Facilitators":
            facilitator_handles = [
                facilitator.strip() for facilitator in lines[i + 2].split(",")
            ]

    if not bootcamp_date:
        raise ValueError("Bootcamp date cannot be empty")
    if not attendee_handles:
        raise ValueError("Attendees cannot be empty")
    if not facilitator_handles:
        raise ValueError("Facilitators cannot be empty")

    logging.info(f"Bootcamp date: {bootcamp_date}")
    logging.info(f"Attendees: {attendee_handles}")
    logging.info(f"Facilitators: {facilitator_handles}")

    return bootcamp_date, attendee_handles, facilitator_handles


# Attendee state factory - builds a list of attendees with their initial state
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

    return attendees


# Create orgs and fork repos
def provision_enironments(
    attendee_state, config, enterprise_id, bootcamp_date, facilitator_state
):
    facilitator_handles = [facilitator["handle"] for facilitator in facilitator_state]
    facilitator_handles.append(config["billing-admin"])

    # Create orgs and fork repos
    for attendee in attendee_state:
        try:
            # If an org_name is too long because the attendee handle is long, only get the first 39 characters
            org_name = (
                config["org-prefix"] + "-" + bootcamp_date + "-" + attendee["handle"]
            )
            if len(org_name) > 39:
                org_name = org_name[0:38]

            org_id, org_name = admin_client.org.create(
                enterprise_id,
                org_name,
                facilitator_handles,
                f"{config['billing-admin']}@spektrasystems.com",
            )
            attendee.update({"org_id": org_id, "org_name": org_name})
        except Exception:
            pass

        for repo in config["repos-to-fork"]:
            try:
                admin_client.repo.fork(repo, attendee["org_name"])
                # Make forked repos private, except for .github
                if repo.split("/")[1] != ".github":
                    forked_repo = attendee["org_name"] + "/" + repo.split("/")[1]
                    # Adding a sleep to avoid race condition when creating a repo and marking it private
                    time.sleep(15)
                    admin_client.repo.visibility(forked_repo, "private")
            except Exception:
                attendee["fork_errors"].append(repo)
                pass

    return attendee_state


def main():
    # Get config
    config = get_config("config.yml")
    for key, value in config.items():
        logging.info(f"{key}: {value}")

    # apply starting label
    issue_ops_client.issue.apply_label(config["labels"]["working"])
    issue_ops_client.issue.remove_label(config["labels"]["new"])

    # Get info from issue
    try:
        bootcamp_date, attendee_handles, facilitator_handles = extract_issue_fields()
    except Exception as e:
        issue_ops_client.issue.apply_label(config["labels"]["error"])
        issue_ops_client.issue.remove_label(config["labels"]["working"])
        issue_ops_client.issue.add_comment(comments.errored)
        issue_ops_client.issue.close()
        sys.exit(1)

    # Get enterprise id
    try:
        enterprise_id = admin_client.enterprise.get_id(config["enterprise"])
    except Exception as e:
        issue_ops_client.issue.apply_label(config["labels"]["error"])
        issue_ops_client.issue.remove_label(config["labels"]["working"])
        issue_ops_client.issue.add_comment(comments.errored)
        issue_ops_client.issue.close()
        sys.exit(1)

    # Build attendee list
    try:
        attendee_state = build_attendees(attendee_handles)
        facilitator_state = build_attendees(facilitator_handles)
    except Exception as e:
        # TODO: Comment and close issue
        issue_ops_client.issue.apply_label(config["labels"]["error"])
        issue_ops_client.issue.remove_label(config["labels"]["working"])
        issue_ops_client.issue.add_comment(comments.errored)
        issue_ops_client.issue.close()
        sys.exit(1)

    # Create bootcamp orgs
    attendee_state = provision_enironments(
        attendee_state, config, enterprise_id, bootcamp_date, facilitator_state
    )

    facilitator_state = provision_enironments(
        facilitator_state, config, enterprise_id, bootcamp_date, facilitator_state
    )

    # Wait for orgs to be created
    wait_time = 30
    logging.info(f"Waiting {wait_time} seconds for orgs to be created")
    time.sleep(wait_time)

    # invite attendees to orgs
    error_count = 0
    for attendee in attendee_state:
        if attendee["org_name"]:
            try:
                admin_client.org.invite_member(attendee["id"], attendee["org_name"])
                attendee["invited"] = True
            except Exception:
                issue_ops_client.issue.apply_label(config["labels"]["error"])
        else:
            error_count += 1

    # Check for provisioning errors
    if error_count > 0:
        issue_ops_client.issue.apply_label(config["labels"]["error"])
        issue_ops_client.issue.remove_label(config["labels"]["working"])
        comment = (
            comments.errored
            + "### Attendees\n\n"
            + comments.attendees_to_markdown(attendee_state)
            + "### Facilitators\n\n"
            + comments.attendees_to_markdown(facilitator_state)
        )
        issue_ops_client.issue.add_comment(comment)
        issue_ops_client.issue.close()
        sys.exit(1)

    # Update the issue with the results
    issue_ops_client.issue.apply_label(config["labels"]["done"])
    issue_ops_client.issue.remove_label(config["labels"]["working"])
    comment = (
        comments.complete
        + "### Attendees\n\n"
        + comments.attendees_to_markdown(attendee_state)
        + "### Facilitators\n\n"
        + comments.attendees_to_markdown(facilitator_state)
    )
    issue_ops_client.issue.add_comment(comment)


if __name__ == "__main__":
    main()

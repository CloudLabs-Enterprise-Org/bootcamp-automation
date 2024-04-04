# GHAS Bootcamp Automation
Hey 👋. This is the repo that handles automation for managing GHAS bootcamp environments.

For GHAS bootcamps, we provision an entire GitHub organization for attendees.  This organization is created in a GitHub enterprise that already has GHAS licenses provisioned.  The reason we create an org instead of just a repo is so the learners are able to fully manage their own GitHub organization and get a better understanding of the enterprise level activities they will need to undertake as managers of a GHAS environment.  

This repository automation handles the creation and destruction of the learner environments.  

## How do I use the automation?
The automation is entirely issue-ops driven. Here's a video to walk you through the process.


https://github.com/ghas-bootcamp-admin/bootcamp-automation/assets/4910518/0a842762-ea13-4b95-b34c-b4cf72584d4d



### Creating a new environment

To create a new bootcamp environment you will need a couple things:
* The list of attendee handles (in csv format)
* The list of facilitator handles (csv format)
* The date of the bootcamp.  

That's it!  Once you have that information, click the button below. 

[![start-new-issue](./assets/button.png)](https://github.com/CloudLabs-Enterprise-Org/bootcamp-automation/issues/new?assignees=&labels=bootcamp::new&projects=&template=create-ghas-bootcamp.yml&title=GHAS+bootcamp+request)

> **Note** 
> Creating a new environment will notify the attendees via email.

Once the automation is complete, a comment will be added to the issue describing the completion state.  The bot will also share a table with links to the learner bootcamp orgs, as well as the facilitator orgs.  

### Decomissioning a bootcamp environment
The process for decomissioning a bootcamp environment is not fully automated (on a schedule) yet. You can manually kick off the teardown process by following these steps:
1. Navigate to **Actions** in this repository
2. Select the **GHAS Bootcamp Teardown** workflow
   
   ![image](https://github.com/ghas-bootcamp-admin/bootcamp-automation/assets/4910518/f0556468-f9cb-4cab-b1f9-1c12e18802dc)
4. Select **Run Workflow** dropdown
   
   ![image](https://github.com/ghas-bootcamp-admin/bootcamp-automation/assets/4910518/30b72285-ab1b-4254-9ecb-c2239e3eb294)
6. Enter the issue number from the creation process that you would like to tear down
   
   ![image](https://github.com/ghas-bootcamp-admin/bootcamp-automation/assets/4910518/a7c56b8d-3ca8-49f7-b040-998fc4480dc9)

The automation process will run and notify you of the completion status.

### Changing configuration settings
The [config.yml](./config.yml) file contains all the settings to control how the automation operates.  There shouldn't be many changes that happen here.  You can configure the following items:
* `enterprise`: This is the name of the enterprise where the bootcamp orgs will be created
* `org-prefix`: This is the prefix that is added to all of the orgs that are created.  
* `billing-email`: This is the user email that will have billing ownership of the created orgs
* `labels`: The labels are used by the automation to communicate status.  Only change these if there's a conflict with your existing labels
* `repos-to-fork`: This is the list of repos that will be forked into the learner orgs.  Since these are forked, the source repos need to be public.

## What does the automation do?
Once the automation is complete, it will create a new org for each attendee with a name in the format of `ghas-bootcamp-<bootcamp date>-<attendee handle>`.  The automation will also create a bootcamp org for each facilitator using the same naming structure as the attendees.

> **Warning**
> It's really important the date in your issue is unique.  We use the date to create entropy in the org name.  The automation will fail if there is a conflict in the naming of the org.

After the creation of the orgs, all of the repos that are listed in the `repos-to-fork` field of [config.yml](./config.yml) will be forked into the bootcamp environments. 

Once the learner orgs are complete, the facilitators will be invited as admins of the learner orgs and notifications are sent out to everyone to join the new orgs.

## Prerequisites
This automation could be used in any GitHub enterprise with GHAS licenses available.  There are a couple pre-reqs that need to be met for the automation to work.  
#### Tokens
You'll need an Actions secret inside this repository titled `ENT_ADMIN_TOKEN`.  This token is used to create the orgs and invite users.  This token needs to have some pretty broad rights.  It needs to be created by an enterprise admin for the enterprise listed in your configuration file.  This token needs to have the following rights:
* `repo`
* `admin:org`
* `user`
* `admin:enterprise`

#### Labels
The labels called out in config.yml will need to be created inside this repository before running the automation for the first time.  This automation doesn't have the ability to create labels for issues, so if the labels don't exist, the automation will fail.








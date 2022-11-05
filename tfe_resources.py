#!/usr/bin/env python3

# Usage:
# Set TFE_TOKEN environment variable
# Supply URL if not using https://app.terraform.io
# ./tfe_resources.py --url https://terraform.companyname.com --output file.csv

import csv
import os
import sys
import argparse
import requests

description = 'Terraform Cloud/Enterprise Resource Inventory to CSV'


class Organizations:
    """Terraform Cloud/Enterprise Organization Class"""

    def __init__(self, id, created_at):
        self.id = id
        self.created_at = created_at


class Workspaces:
    """Terraform Cloud/Enterprise Workspace Class"""

    def __init__(self, id, name, org, date_created, date_changed):
        self.id = id
        self.name = name
        self.org = org
        self.date_created = date_created
        self.date_changed = date_changed


class Resources:
    """Terraform Cloud/Enterprise Resource Class"""

    def __init__(self, name, type, identifier, org, workspace_id, workspace_name):
        self.name = name
        self.type = type
        self.identifier = identifier
        self.org = org
        self.workspace_id = workspace_id
        self.workspace_name = workspace_name


def get_organizations():
    """
    GET /organizations
    https://www.terraform.io/docs/cloud/api/organizations.html#list-organizations
    """
    output = []
    next_page = args.url + '/api/v2/organizations'

    while next_page:

        page = requests.get(next_page, headers=HEADERS, timeout=30)

        if page.status_code == 200:
            for org in page.json()['data']:
                output.append(Organizations(
                    org['id'], org['attributes']['created-at']))

        else:
            print(f"Error ({page.status_code}) getting organizations)")
            sys.exit()

        try:
            next_page = page.json()['links']['next']
        except KeyError:
            next_page = None

    return output


def get_workspaces(data):
    """
    GET /organizations/:organization_name/workspaces
    https://www.terraform.io/docs/cloud/api/workspaces.html#list-workspaces
    """
    output = []

    for org in data:
        next_page = f"{args.url}/api/v2/organizations/{org.id}/workspaces"

        while next_page:

            page = requests.get(next_page, headers=HEADERS, timeout=30)

            if page.status_code == 200:
                for workspace in page.json()['data']:
                    output.append(Workspaces(workspace['id'],
                                             workspace['attributes']['name'],
                                             org.id,
                                             workspace['attributes']['created-at'],
                                             workspace['attributes']['updated-at']))

            else:
                print(
                    f"Error ({page.status_code}) getting workspaces "
                    f"for organization '{org.id}'")
                sys.exit()

            try:
                next_page = page.json()['links']['next']
            except KeyError:
                next_page = None

    return output


def get_resources(data):
    """
    Download state file for workspace and parse resources
    GET /workspaces/:workspace_id/current-state-version
    https://www.terraform.io/docs/cloud/api/state-versions.html#show-a-state-version
    """

    output = []

    for workspace in data:

        next_page = f"{args.url}/api/v2/workspaces/"\
                    f"{workspace.id}/current-state-version"

        page = requests.get(next_page, headers=HEADERS, timeout=30)

        if page.status_code == 200:
            state_url = page.json()[
                'data']['attributes']['hosted-state-download-url']
        else:
            print(
                f"Error ({page.status_code}) getting state for "
                f"workspace '{workspace.name}'")
            sys.exit()

        page = requests.get(state_url, headers=HEADERS, timeout=30)

        if page.status_code == 200:
            for resource in page.json()['resources']:
                name = resource['name']
                type = resource['type']
                for instance in resource['instances']:
                    if "arn" in instance['attributes']:
                        identifier = instance['attributes']['arn']
                    else:
                        identifier = None

                    output.append(Resources(name, type, identifier,
                                            workspace.org, workspace.id, workspace.name))

    return output


def create_csv(data):
    """ Create CSV file from resources list """
    fields = ['name', 'type', 'identifier',
              'org', 'workspace_id', 'workspace_name']

    with open(args.output, 'w', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()
        for resource in data:
            writer.writerow({'name': resource.name,
                            'type': resource.type,
                             'identifier': resource.identifier,
                             'org': resource.org,
                             'workspace_id': resource.workspace_id,
                             'workspace_name': resource.workspace_name})


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--url', help='Parse TFE URL, leave blank for TFC',
                        default='https://app.terraform.io', required=False)
    parser.add_argument('--output', help='Output file name', required=True)

    args = parser.parse_args()

    # Get TFE_TOKEN environment variable
    TOKEN = os.environ.get('TFE_TOKEN')
    HEADERS = {'Authorization': f'Bearer {TOKEN}',
               'Content-Type': 'application/vnd.api+json'}

    if TOKEN is None:
        print('Environment variable TFE_TOKEN not set')
        sys.exit()

    orgs = get_organizations()
    ws = get_workspaces(orgs)
    res = get_resources(ws)
    create_csv(res)

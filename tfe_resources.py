#!/usr/bin/env python3

# Usage:
# Set TFE_TOKEN environment variable
# Supply URL if not using https://app.terraform.io
# ./tfe_resources.py --url https://terraform.companyname.com --output file.csv

import csv
import os
import argparse
import requests

description = 'Terraform Cloud/Enterprise Resource Inventory to CSV'


class organizations:
    def __init__(self, id, created_at):
        self.id = id
        self.created_at = created_at


class workspaces:
    def __init__(self, id, name, org, date_created, date_changed):
        self.id = id
        self.name = name
        self.org = org
        self.date_created = date_created
        self.date_changed = date_changed


class resources:
    def __init__(self, name, type, identifier, org, workspace_id, workspace_name):
        self.name = name
        self.type = type
        self.identifier = identifier
        self.org = org
        self.workspace_id = workspace_id
        self.workspace_name = workspace_name


def get_organizations():
    list = []
    next_page = args.url + '/api/v2/organizations'
    while next_page:
        page = requests.get(next_page, headers=HEADERS)

        if page.status_code == 200:
            for org in page.json()['data']:
                list.append(organizations(
                    org['id'], org['attributes']['created-at']))

        else:
            print('Error ({}) getting organizations'.format(page.status_code))
            exit(1)

        try:
            next_page = page.json()['links']['next']
        except KeyError:
            next_page = None

    return list


def get_workspaces(orgs):
    """
    GET /organizations/:organization_name/workspaces
    https://www.terraform.io/docs/cloud/api/workspaces.html#list-workspaces
    """
    list = []

    for org in orgs:
        next_page = args.url + \
            '/api/v2/organizations/{}/workspaces'.format(org.id)
        while next_page:
            page = requests.get(next_page, headers=HEADERS)
            if page.status_code == 200:
                for workspace in page.json()['data']:
                    list.append(workspaces(workspace['id'],
                                           workspace['attributes']['name'],
                                           org.id,
                                           workspace['attributes']['created-at'],
                                           workspace['attributes']['updated-at']))
            else:
                print('Error ({}) getting workspaces for "{}" organization'.format(
                    page.status_code, org.id))
                exit(1)

            try:
                next_page = page.json()['links']['next']
            except KeyError:
                next_page = None

    return list


def get_current_state(ws):
    """
    Download state file for workspace and parse resources
    GET /workspaces/:workspace_id/current-state-version
    https://www.terraform.io/docs/cloud/api/state-versions.html#show-a-state-version
    """

    list = []

    for workspace in ws:
        next_page = args.url + \
            '/api/v2/workspaces/{}/current-state-version'.format(workspace.id)
        page = requests.get(next_page, headers=HEADERS)

        if (page.status_code == 200):
            state_url = page.json()[
                'data']['attributes']['hosted-state-download-url']
        else:
            print('Error ({}) getting state for "{}" workspace'.format(
                page.status_code, workspace.name))
            exit(1)

        page = requests.get(state_url, headers=HEADERS)
        if (page.status_code == 200):
            for resource in page.json()['resources']:
                name = resource['name']
                type = resource['type']
                for instance in resource['instances']:
                    if "arn" in instance['attributes']:
                        identifier = instance['attributes']['arn']
                    else:
                        identifier = None

                    list.append(resources(name, type, identifier,
                                workspace.org, workspace.id, workspace.name))

    return list


def create_csv(resources):
    fields = ['name', 'type', 'identifier',
              'org', 'workspace_id', 'workspace_name']

    with open(args.output, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()
        for resource in resources:
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
    HEADERS = {'Authorization': 'Bearer ' + TOKEN,
               'Content-Type': 'application/vnd.api+json'}

    if TOKEN is None:
        print('Environment variable TFE_TOKEN not set')
        exit(1)

    orgs = get_organizations()
    ws = get_workspaces(orgs)
    res = get_current_state(ws)
    create_csv(res)

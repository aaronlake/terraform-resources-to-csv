# tfe_resources.py

This Python script will retrieve all of the resources from Terraform
Enterprise (TFE) or Terraform Cloud (TFC) and output them to a CSV file with
their Workspace and Organization.

## Usage

Install Prerequisites:

    pip install -r requirements.txt

Export the following environment variables:

    export TFE_TOKEN=<your TFE token>

Run the script:

    python3 tfe_resources.py --url <your TFE URL> --output <output file>

## Todo

[ ] Handle `next-page`
[ ] Handle non-AWS cloud providers

# Integration Setup Guide

This document provides an overview of the integration marketplace, connection workflow, and troubleshooting tips for common integrations.

## Marketplace Overview

The marketplace exposes a curated list of integrations that can be connected per tenant. Each integration includes a sample payload to help validate webhook handling.

## Connection Workflow

1. List available integrations to discover supported services.
2. Choose an integration and provide the destination URL or key.
3. The system probes the webhook for reachability and performance.
4. On success, the configuration is stored for the tenant.

## Troubleshooting

If connection fails, verify the following:

- **Self-signed TLS**: Use a certificate from a trusted authority.
- **Slow responses**: Ensure the endpoint responds within one second.

## Slack

1. Navigate to *Incoming Webhooks* in Slack and create a new webhook URL.
2. Use the generated URL when connecting the integration.
3. Confirm messages appear in the selected channel.

![Slack setup](images/slack_setup.png)

## Google Sheets

1. Create a script endpoint that appends rows to a sheet.
2. Publish the script as a web app and obtain the URL.
3. Provide this URL during connection and test with sample payloads.

![Google Sheets setup](images/google_sheets_setup.png)

## Zoho Books

1. Enable webhooks in Zoho Books and create a new rule.
2. Enter the webhook URL provided by Neo.
3. Verify invoices trigger the webhook on payment events.

![Zoho Books setup](images/zoho_books_setup.png)


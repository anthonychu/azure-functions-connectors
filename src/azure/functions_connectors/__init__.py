import logging

from ._client import ConnectorClient, ConnectorError
from ._clients.gmail import GmailClient
from ._clients.googlecalendar import GoogleCalendarClient
from ._clients.office365 import Office365Client
from ._clients.salesforce import SalesforceClient
from ._clients.sharepoint import SharePointClient
from ._clients.teams import TeamsClient
from ._decorator import FunctionsConnectors
from ._models import ConnectorItem
from ._registration import register_connector_triggers
from ._triggers.gmail import GmailEmail, GmailTriggers
from ._triggers.googlecalendar import GoogleCalendarEvent, GoogleCalendarTriggers
from ._triggers.office365 import Office365Email, Office365Event, Office365Triggers
from ._triggers.salesforce import SalesforceRecord, SalesforceTriggers
from ._triggers.sharepoint import SharePointFile, SharePointItem, SharePointTriggers
from ._triggers.teams import TeamsChannel, TeamsMessage, TeamsTriggers

__all__ = [
    "ConnectorClient",
    "ConnectorError",
    "ConnectorItem",
    "FunctionsConnectors",
    "GmailClient",
    "GmailEmail",
    "GmailTriggers",
    "GoogleCalendarClient",
    "GoogleCalendarEvent",
    "GoogleCalendarTriggers",
    "Office365Client",
    "Office365Email",
    "Office365Event",
    "Office365Triggers",
    "SalesforceClient",
    "SalesforceRecord",
    "SalesforceTriggers",
    "SharePointClient",
    "SharePointFile",
    "SharePointItem",
    "SharePointTriggers",
    "TeamsChannel",
    "TeamsClient",
    "TeamsMessage",
    "TeamsTriggers",
    "register_connector_triggers",
]

# Suppress noisy Azure SDK HTTP transport logs.
# Set at the root 'azure' logger to catch all SDK loggers before they're created.
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure.storage").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)

"""Phase 2 business-operations HTTP Marketplace Apps (metadata only)."""

from __future__ import annotations

from gen_lib import enum_field, field, person_field, slot, trigger, write_http_app
from http_tools import get_tool, owned_customer, write_tool

EMAIL_ALSO = [
    {"identity": "person.external_id", "paths": ["id", "requester_id", "contact.id"]},
    {"identity": "person.phone", "paths": ["phone", "mobile"]},
]


def _readme(title: str, app_id: str, body: str) -> str:
    return f"""# {app_id}

Metadata Marketplace App for {title}.

- **App id:** `{app_id}`
- **Hosting:** `runtime`
- **Execution:** generic HTTP tools against a workspace connection

There is no vendor SDK, webhook server, or API client in this package.

{body}
"""


def freshdesk_app() -> None:
    conn = "freshdesk"
    write_http_app(
        {
            "id": "freshdesk-runtime",
            "name": "Freshdesk",
            "description": "Contacts, tickets, comments, agents, and ticket status as a metadata Marketplace App",
            "category": "support",
            "tags": ["freshdesk", "support", "runtime"],
            "comments": [
                "Freshdesk — metadata Marketplace App (hosting: runtime).",
                "No Freshdesk SDK. Workspace supplies {subdomain}.freshdesk.com and Bearer/API key.",
            ],
            "connection": {
                "_comments": [
                    "host_suffix constrains Connect to *.freshdesk.com. No subdomain or API key in YAML.",
                ],
                "id": conn,
                "auth_type": "bearer",
                "oauth": {"host_suffix": ".freshdesk.com"},
                "webhooks": {
                    "hmac": {
                        "algorithm": "hmac-sha256",
                        "encoding": "hex",
                        "header": "X-Freshdesk-Signature",
                        "key_source": "app_client",
                    },
                    "identity_header": "X-Freshdesk-Account",
                    "topic_header": "X-Freshdesk-Event",
                    "event_id_header": "X-Freshdesk-Webhook-Id",
                    "topics": {
                        "ticket_created": "ticket.created",
                        "ticket_updated": "ticket.updated",
                        "ticket_deleted": "ticket.cancelled",
                        "contact_created": "contact.created",
                    },
                },
            },
            "tools": [
                get_tool("list_contacts", "Staff-only contact list on the workspace HTTP connection", conn, "/api/v2/contacts", items="contacts"),
                get_tool("get_contact", "Staff-only contact fetch by id", conn, "/api/v2/contacts/{id}", paginate=False),
                get_tool("list_tickets", "Staff-only ticket list on the workspace HTTP connection", conn, "/api/v2/tickets", items="tickets"),
                get_tool("get_ticket", "Staff-only ticket fetch by id", conn, "/api/v2/tickets/{id}", paginate=False),
                get_tool("list_my_tickets", "List tickets for the authenticated conversation Person only. Do not pass email, phone, person_id, or customer_id.", conn, "/api/v2/tickets", items="tickets", query={"email": "{person.email}"}, staff=False, customer=owned_customer(["email", "requester.email"], also=EMAIL_ALSO)),
                write_tool("create_ticket", "Staff-only create a support ticket", conn, "POST", "/api/v2/tickets", body={"subject": "{subject}", "description": "{description}", "email": "{requester_email}", "status": 2, "priority": 1}),
                write_tool("update_ticket", "Staff-only update ticket status or fields", conn, "PUT", "/api/v2/tickets/{id}", body={"status": "{status}", "priority": "{priority}"}),
                get_tool("list_ticket_comments", "Staff-only ticket conversations/comments", conn, "/api/v2/tickets/{id}/conversations", items="conversations"),
                write_tool("create_ticket_comment", "Staff-only add a ticket note/comment", conn, "POST", "/api/v2/tickets/{id}/notes", body={"body": "{body}", "private": False}),
                get_tool("list_agents", "Staff-only agent list on the workspace HTTP connection", conn, "/api/v2/agents", items="agents"),
            ],
            "entities": [
                {"id": "contact", "name": "Contact", "description": "Freshdesk contact bound to Person", "prefix": "C-", "fields": [field("name", "string", True), field("email", "email"), field("phone", "phone"), person_field("Existing Qefro Person identity")]},
                {"id": "ticket", "name": "Ticket", "description": "Support ticket", "prefix": "T-", "fields": [field("subject", "string", True), field("description", "string"), enum_field("status", ["open", "pending", "resolved", "closed"]), person_field("Existing Qefro Person identity")]},
                {"id": "ticket_comment", "name": "Ticket comment", "description": "Note or reply on a ticket", "fields": [field("body", "string", True), field("ticket_id", "string")]},
                {"id": "agent", "name": "Agent", "description": "Support agent", "fields": [field("name", "string", True), field("email", "email")]},
            ],
            "flows": [
                {"id": "create-support-ticket", "name": "Create support ticket", "description": "Create a Freshdesk ticket through generic Runtime HTTP", "tool": "create_ticket", "ask": {"field": "subject", "message": "What is the ticket subject?"}, "extra_asks": [{"field": "description", "message": "Describe the issue."}, {"field": "requester_email", "message": "Requester email on the ticket?"}], "confirm": "Ticket created: {{subject}}."},
                {"id": "update-ticket", "name": "Update ticket", "description": "Update ticket status through generic Runtime HTTP", "tool": "update_ticket", "ask": {"field": "id", "message": "Which ticket id?"}, "extra_asks": [{"field": "status", "message": "New status code?"}, {"field": "priority", "message": "New priority code?"}], "confirm": "Ticket {{id}} updated."},
                {"id": "list-my-tickets", "name": "List my tickets", "description": "Show the authenticated customer's tickets", "tool": "list_my_tickets", "confirm": "Here are your tickets.\n{{items_text}}"},
                {"id": "add-ticket-comment", "name": "Add ticket comment", "description": "Add a comment through generic Runtime HTTP", "tool": "create_ticket_comment", "ask": {"field": "id", "message": "Which ticket id?"}, "extra_asks": [{"field": "body", "message": "Comment text?"}], "confirm": "Comment added to ticket {{id}}."},
            ],
            "events": ["ticket.created", "ticket.updated", "ticket.cancelled", "contact.created"],
            "triggers": [
                trigger("create_support_ticket", "create-support-ticket", "ticket_input", ["create a support ticket", "open a ticket", "file a ticket"], ["ticket created"], ["subject"], "Ticket created: {{subject}}."),
                trigger("update_ticket", "update-ticket", "ticket_update", ["update the ticket", "change ticket status"], ["updated"], ["id"], "Ticket {{id}} updated."),
                trigger("list_my_tickets", "list-my-tickets", "my_ticket_list", ["show my tickets", "my support tickets"], ["your tickets"], [], "Here are your tickets."),
                trigger("add_ticket_comment", "add-ticket-comment", "comment_input", ["add a ticket comment", "reply on the ticket"], ["comment added"], ["id"], "Comment added to ticket {{id}}."),
            ],
            "slots": [
                slot("subject", ["subject", "title"], "string"),
                slot("description", ["description", "issue", "details"], "string"),
                slot("requester_email", ["requester", "contact email"], "string"),
                slot("id", ["ticket", "ticket id"], "string"),
                slot("status", ["status"], "string"),
                slot("priority", ["priority"], "string"),
                slot("body", ["comment", "note", "reply"], "string"),
            ],
            "intro": "Metadata Marketplace App. Chat “create a support ticket” or “show my tickets” runs generic Runtime HTTP. Contacts stay on Person CRM. Automations subscribe to ticket.created.",
            "theme": {"primary": "#2c68ff", "secondary": "#12344d", "accent": "#00a886", "background": "#f5f7f9", "surface": "#ffffff", "text": "#12344d"},
            "sources": [("contacts", "contact"), ("tickets", "ticket"), ("agents", "agent")],
            "tables": [
                {"id": "tickets_table", "title": "Tickets", "source": "tickets", "icon": "receipt", "columns": [{"key": "subject", "header": "Subject"}, {"key": "status", "header": "Status"}]},
                {"id": "contacts_table", "title": "Freshdesk contacts", "source": "contacts", "page_id": "fd-contacts", "icon": "users", "columns": [{"key": "name", "header": "Name"}, {"key": "email", "header": "Email"}]},
                {"id": "agents_table", "title": "Agents", "source": "agents", "icon": "user", "columns": [{"key": "name", "header": "Name"}, {"key": "email", "header": "Email"}]},
            ],
            "form": {
                "id": "ticket_form",
                "title": "New ticket",
                "page": "tickets",
                "trigger": "create-support-ticket",
                "submit_label": "Create ticket",
                "fields": [
                    {"name": "subject", "label": "Subject", "type": "text", "required": True},
                    {"name": "description", "label": "Description", "type": "text", "required": True},
                    {"name": "requester_email", "label": "Requester email", "type": "text", "required": True},
                ],
            },
            "status": {"id": "tickets_status", "title": "Tickets", "source": "tickets", "label_field": "subject"},
            "readme": _readme(
                "Freshdesk",
                "freshdesk-runtime",
                """## Connection

Bearer credential. `oauth.host_suffix: .freshdesk.com` so Connect cannot point at an arbitrary host.

create_ticket uses `requester_email` (not `email`) so LLM/client parameters cannot override Hub identity keys.

## CRM Automation examples

- `ticket.created` → create CRM activity, notify staff
- `ticket.updated` → notify assignee

## Webhooks

Declared HMAC/topic headers. Freshdesk automations may use a different signature envelope — treat as generic HMAC first.
""",
            ),
        }
    )


def zoho_crm_app() -> None:
    conn = "zoho-crm"
    write_http_app(
        {
            "id": "zoho-crm-runtime",
            "name": "Zoho CRM",
            "description": "Leads, contacts, accounts, deals, notes, and activities as a metadata Marketplace App",
            "category": "crm",
            "tags": ["zoho", "crm", "runtime"],
            "comments": [
                "Zoho CRM — metadata Marketplace App (hosting: runtime).",
                "Staff-only HTTP. Customer Hub remains the Qefro Person model.",
            ],
            "connection": {
                "id": conn,
                "auth_type": "bearer",
                "oauth": {
                    "authorize_url": "https://accounts.zoho.com/oauth/v2/auth",
                    "token_url": "https://accounts.zoho.com/oauth/v2/token",
                    "revoke_url": "https://accounts.zoho.com/oauth/v2/token/revoke",
                    "revoke_method": "POST",
                    "scopes": [
                        "ZohoCRM.modules.ALL",
                        "ZohoCRM.settings.ALL",
                    ],
                },
                "webhooks": {
                    "hmac": {
                        "algorithm": "hmac-sha256",
                        "encoding": "hex",
                        "header": "X-ZOHO-WEBHOOK-SIGNATURE",
                        "key_source": "app_client",
                    },
                    "identity_header": "X-ZOHO-ORG",
                    "topic_header": "X-ZOHO-EVENT",
                    "event_id_header": "X-ZOHO-WEBHOOK-ID",
                    "topics": {
                        "Leads.create": "lead.created",
                        "Contacts.create": "contact.created",
                        "Deals.create": "deal.created",
                        "Deals.edit": "deal.updated",
                    },
                },
            },
            "tools": [
                get_tool("list_leads", "Staff-only lead list on the workspace HTTP connection", conn, "/crm/v2/Leads", items="data", scopes=["ZohoCRM.modules.ALL"]),
                get_tool("get_lead", "Staff-only lead fetch", conn, "/crm/v2/Leads/{id}", paginate=False, scopes=["ZohoCRM.modules.ALL"]),
                write_tool("create_lead", "Staff-only create a lead", conn, "POST", "/crm/v2/Leads", body={"data": [{"Last_Name": "{last_name}", "Email": "{lead_email}", "Company": "{company}"}]}, scopes=["ZohoCRM.modules.ALL"]),
                get_tool("list_contacts", "Staff-only contact list on the workspace HTTP connection", conn, "/crm/v2/Contacts", items="data", scopes=["ZohoCRM.modules.ALL"]),
                get_tool("list_accounts", "Staff-only account list on the workspace HTTP connection", conn, "/crm/v2/Accounts", items="data", scopes=["ZohoCRM.modules.ALL"]),
                get_tool("list_deals", "Staff-only deal list on the workspace HTTP connection", conn, "/crm/v2/Deals", items="data", scopes=["ZohoCRM.modules.ALL"]),
                write_tool("create_deal", "Staff-only create a deal", conn, "POST", "/crm/v2/Deals", body={"data": [{"Deal_Name": "{deal_name}", "Stage": "{stage}"}]}, scopes=["ZohoCRM.modules.ALL"]),
                write_tool("create_note", "Staff-only create a note", conn, "POST", "/crm/v2/Notes", body={"data": [{"Note_Title": "{title}", "Note_Content": "{body}", "Parent_Id": "{parent_id}"}]}, scopes=["ZohoCRM.modules.ALL"]),
                get_tool("list_activities", "Staff-only activities/events list", conn, "/crm/v2/Events", items="data", scopes=["ZohoCRM.modules.ALL"]),
            ],
            "entities": [
                {"id": "lead", "name": "Lead", "description": "Zoho lead", "prefix": "L-", "fields": [field("last_name", "string", True), field("company", "string"), field("lead_email", "email")]},
                {"id": "contact", "name": "Contact", "description": "Zoho contact bound to Person", "fields": [field("name", "string", True), field("email", "email"), person_field("Existing Qefro Person identity")]},
                {"id": "account", "name": "Account", "description": "Zoho account", "fields": [field("name", "string", True), field("phone", "phone")]},
                {"id": "deal", "name": "Deal", "description": "Zoho deal", "prefix": "D-", "fields": [field("deal_name", "string", True), field("stage", "string")]},
                {"id": "note", "name": "Note", "description": "CRM note", "fields": [field("title", "string", True), field("body", "string")]},
                {"id": "activity", "name": "Activity", "description": "Event or task", "fields": [field("subject", "string", True), field("start", "datetime")]},
            ],
            "flows": [
                {"id": "create-lead", "name": "Create lead", "description": "Create a Zoho lead through generic Runtime HTTP", "tool": "create_lead", "ask": {"field": "last_name", "message": "Lead last name?"}, "extra_asks": [{"field": "lead_email", "message": "Lead email?"}, {"field": "company", "message": "Company?"}], "confirm": "Lead created for {{last_name}}."},
                {"id": "create-deal", "name": "Create deal", "description": "Create a Zoho deal through generic Runtime HTTP", "tool": "create_deal", "ask": {"field": "deal_name", "message": "Deal name?"}, "extra_asks": [{"field": "stage", "message": "Stage?"}], "confirm": "Deal {{deal_name}} created."},
                {"id": "create-note", "name": "Create note", "description": "Create a Zoho note through generic Runtime HTTP", "tool": "create_note", "ask": {"field": "title", "message": "Note title?"}, "extra_asks": [{"field": "body", "message": "Note content?"}, {"field": "parent_id", "message": "Parent record id?"}], "confirm": "Note {{title}} created."},
                {"id": "list-deals", "name": "List deals", "description": "Staff list deals through generic Runtime HTTP", "tool": "list_deals", "confirm": "Here are the recent deals.\n{{items_text}}"},
            ],
            "events": ["lead.created", "contact.created", "deal.created", "deal.updated"],
            "triggers": [
                trigger("create_lead", "create-lead", "lead_input", ["create a lead", "add a zoho lead"], ["lead created"], ["last_name"], "Lead created for {{last_name}}."),
                trigger("create_deal", "create-deal", "deal_input", ["create a deal", "add a zoho deal"], ["deal"], ["deal_name"], "Deal {{deal_name}} created."),
                trigger("create_note", "create-note", "note_input", ["add a crm note", "create a note"], ["note"], ["title"], "Note {{title}} created."),
                trigger("list_deals", "list-deals", "deal_list", ["list deals", "show zoho deals"], ["deals"], [], "Here are the recent deals."),
            ],
            "slots": [
                slot("last_name", ["last name", "lead"], "string"),
                slot("lead_email", ["lead email"], "string"),
                slot("company", ["company", "account"], "string"),
                slot("deal_name", ["deal", "opportunity"], "string"),
                slot("stage", ["stage"], "string"),
                slot("title", ["title", "note title"], "string"),
                slot("body", ["note", "content"], "string"),
                slot("parent_id", ["parent", "record id"], "string"),
            ],
            "intro": "Metadata Marketplace App. Staff CRM operations run generic Runtime HTTP against the workspace Zoho connection. Qefro Person CRM stays canonical for Customer Hub.",
            "theme": {"primary": "#c8202b", "secondary": "#111827", "accent": "#e42527", "background": "#f9fafb", "surface": "#ffffff", "text": "#111827"},
            "sources": [("leads", "lead"), ("contacts", "contact"), ("accounts", "account"), ("deals", "deal")],
            "tables": [
                {"id": "leads_table", "title": "Leads", "source": "leads", "icon": "users", "columns": [{"key": "last_name", "header": "Name"}, {"key": "company", "header": "Company"}]},
                {"id": "contacts_table", "title": "Zoho contacts", "source": "contacts", "page_id": "zoho-contacts", "icon": "user", "columns": [{"key": "name", "header": "Name"}, {"key": "email", "header": "Email"}]},
                {"id": "accounts_table", "title": "Accounts", "source": "accounts", "icon": "clipboard", "columns": [{"key": "name", "header": "Name"}]},
                {"id": "deals_table", "title": "Deals", "source": "deals", "icon": "report", "columns": [{"key": "deal_name", "header": "Deal"}, {"key": "stage", "header": "Stage"}]},
            ],
            "form": {
                "id": "lead_form",
                "title": "New lead",
                "page": "leads",
                "trigger": "create-lead",
                "submit_label": "Create lead",
                "fields": [
                    {"name": "last_name", "label": "Last name", "type": "text", "required": True},
                    {"name": "lead_email", "label": "Email", "type": "text", "required": False},
                    {"name": "company", "label": "Company", "type": "text", "required": False},
                ],
            },
            "status": {"id": "deals_status", "title": "Deals", "source": "deals", "label_field": "deal_name"},
            "readme": _readme(
                "Zoho CRM",
                "zoho-crm-runtime",
                """## Connection / OAuth

Bearer OAuth. Scopes `ZohoCRM.modules.ALL` and `ZohoCRM.settings.ALL`. Host typically `www.zohoapis.com` (workspace-supplied). Staff-only.

Lead email uses parameter `lead_email`, never `email`, so callers cannot override Hub identity keys.

## CRM Automation examples

- `lead.created` → create Qefro Person follow-up task
- `deal.updated` → notify staff
""",
            ),
        }
    )


def whatsapp_business_app() -> None:
    conn = "whatsapp-business"
    write_http_app(
        {
            "id": "whatsapp-business-runtime",
            "name": "WhatsApp Business",
            "description": "Cloud API contacts, templates, outbound messages, and message events as a metadata Marketplace App",
            "category": "messaging",
            "tags": ["whatsapp", "messaging", "runtime"],
            "comments": [
                "WhatsApp Business Cloud API — metadata Marketplace App.",
                "This is not the Qefro WhatsApp channel ingest. It does not replace ACS WhatsApp.",
                "No Meta SDK or webhook server in this package.",
            ],
            "connection": {
                "id": conn,
                "auth_type": "bearer",
                "webhooks": {
                    "hmac": {
                        "algorithm": "hmac-sha256",
                        "encoding": "hex",
                        "header": "X-Hub-Signature-256",
                        "key_source": "app_client",
                    },
                    "identity_header": "X-Hub-Account-Id",
                    "topic_header": "X-Hub-Event",
                    "event_id_header": "X-Hub-Delivery-Id",
                    "topics": {
                        "messages": "message.inbound",
                        "message_status": "message.status",
                        "message_template_status_update": "template.updated",
                    },
                },
            },
            "tools": [
                get_tool("list_templates", "Staff-only message template list", conn, "/v21.0/{waba_id}/message_templates", items="data"),
                write_tool("send_template_message", "Staff-only send a template message to a WhatsApp number collected as a slot (not Hub phone override)", conn, "POST", "/v21.0/{phone_number_id}/messages", body={"messaging_product": "whatsapp", "to": "{destination_number}", "type": "template", "template": {"name": "{template_name}", "language": {"code": "{language}"}}}),
                write_tool("send_text_message", "Staff-only send a text message", conn, "POST", "/v21.0/{phone_number_id}/messages", body={"messaging_product": "whatsapp", "to": "{destination_number}", "type": "text", "text": {"body": "{body}"}}),
                get_tool("get_contact", "Staff-only look up a Cloud API contact by wa_id", conn, "/v21.0/{phone_number_id}/contacts", query={"wa_id": "{wa_id}"}, paginate=False),
            ],
            "entities": [
                {"id": "wa_contact", "name": "WhatsApp contact", "description": "Cloud API contact bound to Person", "fields": [field("wa_id", "string", True), field("name", "string"), person_field("Existing Qefro Person identity")]},
                {"id": "message_template", "name": "Message template", "description": "Approved Cloud API template", "fields": [field("name", "string", True), field("language", "string"), enum_field("status", ["APPROVED", "PENDING", "REJECTED"])]},
                {"id": "outbound_message", "name": "Outbound message", "description": "Staff-sent Cloud API message", "fields": [field("destination_number", "string", True), field("template_name", "string"), enum_field("status", ["queued", "sent", "delivered", "read", "failed"])]},
            ],
            "flows": [
                {"id": "send-template-message", "name": "Send template message", "description": "Send a WhatsApp template through generic Runtime HTTP", "tool": "send_template_message", "ask": {"field": "phone_number_id", "message": "Which phone-number id should send?"}, "extra_asks": [{"field": "waba_id", "message": "WABA id (if needed for templates)?"}, {"field": "destination_number", "message": "Destination WhatsApp number?"}, {"field": "template_name", "message": "Template name?"}, {"field": "language", "message": "Template language code?"}], "confirm": "Template {{template_name}} sent."},
                {"id": "send-text-message", "name": "Send text message", "description": "Send a WhatsApp text through generic Runtime HTTP", "tool": "send_text_message", "ask": {"field": "phone_number_id", "message": "Which phone-number id should send?"}, "extra_asks": [{"field": "destination_number", "message": "Destination WhatsApp number?"}, {"field": "body", "message": "Message text?"}], "confirm": "Message sent to {{destination_number}}."},
                {"id": "list-templates", "name": "List templates", "description": "List Cloud API templates through generic Runtime HTTP", "tool": "list_templates", "ask": {"field": "waba_id", "message": "Which WABA id?"}, "confirm": "Here are the templates.\n{{items_text}}"},
            ],
            "events": ["message.inbound", "message.status", "template.updated"],
            "triggers": [
                trigger("send_template_message", "send-template-message", "template_input", ["send a whatsapp template", "send template message"], ["sent"], ["template_name"], "Template {{template_name}} sent."),
                trigger("send_text_message", "send-text-message", "text_input", ["send a whatsapp message", "send text on whatsapp"], ["sent"], ["destination_number"], "Message sent to {{destination_number}}."),
                trigger("list_templates", "list-templates", "template_list", ["list whatsapp templates", "show message templates"], ["templates"], ["waba_id"], "Here are the templates."),
            ],
            "slots": [
                slot("phone_number_id", ["phone number id", "sender id"], "string"),
                slot("waba_id", ["waba", "business account"], "string"),
                slot("destination_number", ["destination", "whatsapp number", "to"], "string"),
                slot("template_name", ["template"], "string"),
                slot("language", ["language", "locale"], "string"),
                slot("body", ["message", "text"], "string"),
                slot("wa_id", ["wa id", "contact id"], "string"),
            ],
            "intro": "Metadata Marketplace App for Meta Cloud API. This is not Qefro WhatsApp channel ingest. Staff send tools; inbound and status arrive as Business Events from webhooks. Surface restrictions stay staff or customer in metadata — never channel branches.",
            "theme": {"primary": "#25d366", "secondary": "#075e54", "accent": "#128c7e", "background": "#f0f2f5", "surface": "#ffffff", "text": "#111b21"},
            "sources": [("wa_contacts", "wa_contact"), ("templates", "message_template"), ("messages", "outbound_message")],
            "tables": [
                {"id": "templates_table", "title": "Templates", "source": "templates", "icon": "list", "columns": [{"key": "name", "header": "Name"}, {"key": "status", "header": "Status"}]},
                {"id": "messages_table", "title": "Outbound", "source": "messages", "icon": "activity", "columns": [{"key": "destination_number", "header": "To"}, {"key": "status", "header": "Status"}]},
                {"id": "contacts_table", "title": "WA contacts", "source": "wa_contacts", "icon": "users", "columns": [{"key": "name", "header": "Name"}, {"key": "wa_id", "header": "WA id"}]},
            ],
            "form": {
                "id": "send_form",
                "title": "Send template",
                "page": "messages",
                "trigger": "send-template-message",
                "submit_label": "Send",
                "fields": [
                    {"name": "phone_number_id", "label": "Phone number id", "type": "text", "required": True},
                    {"name": "destination_number", "label": "Destination number", "type": "text", "required": True},
                    {"name": "template_name", "label": "Template", "type": "text", "required": True},
                    {"name": "language", "label": "Language", "type": "text", "required": True},
                ],
            },
            "status": {"id": "messages_status", "title": "Outbound", "source": "messages", "label_field": "destination_number"},
            "readme": _readme(
                "WhatsApp Business Cloud API",
                "whatsapp-business-runtime",
                """## Connection

Bearer system-user token. Host typically `graph.facebook.com`. `phone_number_id` / `waba_id` are staff parameters, not secrets and not Hub `phone`.

This app does **not** replace Qefro's WhatsApp channel. Surface restrictions stay `staff` / `customer` in metadata.

## CRM Automation examples

- `message.inbound` → create CRM activity, notify staff
- `message.status` → update conversation state

## Webhooks

`X-Hub-Signature-256` hex HMAC (`sha256=` prefix is already stripped by generic hex verify). Topic/identity headers may need JSON-body mapping if Meta does not send them.
""",
            ),
        }
    )


def calendly_app() -> None:
    conn = "calendly"
    write_http_app(
        {
            "id": "calendly-runtime",
            "name": "Calendly",
            "description": "Event types, scheduled events, invitees, and cancellations as a metadata Marketplace App",
            "category": "scheduling",
            "tags": ["calendly", "booking", "runtime"],
            "comments": [
                "Calendly — metadata Marketplace App (hosting: runtime).",
            ],
            "connection": {
                "id": conn,
                "auth_type": "bearer",
                "oauth": {
                    "authorize_url": "https://auth.calendly.com/oauth/authorize",
                    "token_url": "https://auth.calendly.com/oauth/token",
                    "revoke_url": "https://auth.calendly.com/oauth/revoke",
                    "revoke_method": "POST",
                    "scopes": ["default"],
                },
                "webhooks": {
                    "hmac": {
                        "algorithm": "hmac-sha256",
                        "encoding": "hex",
                        "header": "Calendly-Webhook-Signature",
                        "key_source": "app_client",
                    },
                    "identity_header": "Calendly-Organization",
                    "topic_header": "Calendly-Event",
                    "event_id_header": "Calendly-Webhook-Id",
                    "register_url": "https://{host}/api/v2/webhook_subscriptions",
                    "topics": {
                        "invitee.created": "booking.created",
                        "invitee.canceled": "booking.cancelled",
                        "event_type.created": "event_type.created",
                    },
                },
            },
            "tools": [
                get_tool("list_event_types", "Staff-only event type list", conn, "/api/v2/event_types", items="collection"),
                get_tool("list_scheduled_events", "Staff-only scheduled event list", conn, "/api/v2/scheduled_events", items="collection"),
                get_tool("get_scheduled_event", "Staff-only scheduled event fetch", conn, "/api/v2/scheduled_events/{uuid}", paginate=False),
                get_tool("list_invitees", "Staff-only invitees for a scheduled event", conn, "/api/v2/scheduled_events/{uuid}/invitees", items="collection"),
                get_tool("list_my_scheduled_events", "List scheduled events for the authenticated conversation Person only. Do not pass email, phone, person_id, or customer_id.", conn, "/api/v2/scheduled_events", items="collection", query={"invitee_email": "{person.email}"}, staff=False, customer=owned_customer(["email", "invitee.email"])),
                write_tool("cancel_scheduled_event", "Staff-only cancel a scheduled event", conn, "POST", "/api/v2/scheduled_events/{uuid}/cancellation", body={"reason": "{reason}"}),
            ],
            "entities": [
                {"id": "event_type", "name": "Event type", "description": "Bookable Calendly event type", "fields": [field("name", "string", True), field("duration", "integer")]},
                {"id": "scheduled_event", "name": "Scheduled event", "description": "Booked event", "prefix": "B-", "fields": [field("name", "string", True), field("start", "datetime"), enum_field("status", ["active", "canceled"]), person_field("Existing Qefro Person identity")]},
                {"id": "invitee", "name": "Invitee", "description": "Event invitee bound to Person", "fields": [field("name", "string"), field("email", "email"), person_field("Existing Qefro Person identity")]},
            ],
            "flows": [
                {"id": "list-event-types", "name": "List event types", "description": "List Calendly event types through generic Runtime HTTP", "tool": "list_event_types", "confirm": "Here are the event types.\n{{items_text}}"},
                {"id": "list-my-bookings", "name": "List my bookings", "description": "Show the authenticated customer's Calendly bookings", "tool": "list_my_scheduled_events", "confirm": "Here are your bookings.\n{{items_text}}"},
                {"id": "cancel-booking", "name": "Cancel booking", "description": "Cancel a scheduled event through generic Runtime HTTP", "tool": "cancel_scheduled_event", "ask": {"field": "uuid", "message": "Which scheduled event uuid?"}, "extra_asks": [{"field": "reason", "message": "Cancellation reason?"}], "confirm": "Booking {{uuid}} cancelled."},
                {"id": "list-invitees", "name": "List invitees", "description": "List invitees through generic Runtime HTTP", "tool": "list_invitees", "ask": {"field": "uuid", "message": "Which scheduled event uuid?"}, "confirm": "Invitees for {{uuid}}.\n{{items_text}}"},
            ],
            "events": ["booking.created", "booking.cancelled", "event_type.created"],
            "triggers": [
                trigger("list_event_types", "list-event-types", "event_type_list", ["list event types", "what can I book"], ["event types"], [], "Here are the event types."),
                trigger("list_my_bookings", "list-my-bookings", "my_booking_list", ["show my bookings", "my calendly events"], ["your bookings"], [], "Here are your bookings."),
                trigger("cancel_booking", "cancel-booking", "cancel_input", ["cancel my booking", "cancel the calendly event"], ["cancelled"], ["uuid"], "Booking {{uuid}} cancelled."),
                trigger("list_invitees", "list-invitees", "invitee_list", ["list invitees", "who is invited"], ["invitees"], ["uuid"], "Invitees for {{uuid}}."),
            ],
            "slots": [
                slot("uuid", ["event", "booking", "uuid"], "string"),
                slot("reason", ["reason", "cancellation"], "string"),
            ],
            "intro": "Metadata Marketplace App. Chat “show my bookings” uses Hub email. Staff cancel uses generic HTTP. Automations subscribe to booking.created.",
            "theme": {"primary": "#0069ff", "secondary": "#0b1f33", "accent": "#0069ff", "background": "#f5f7fa", "surface": "#ffffff", "text": "#0b1f33"},
            "sources": [("event_types", "event_type"), ("scheduled_events", "scheduled_event"), ("invitees", "invitee")],
            "tables": [
                {"id": "types_table", "title": "Event types", "source": "event_types", "icon": "calendar", "columns": [{"key": "name", "header": "Name"}, {"key": "duration", "header": "Minutes"}]},
                {"id": "events_table", "title": "Scheduled", "source": "scheduled_events", "icon": "clock", "columns": [{"key": "name", "header": "Name"}, {"key": "status", "header": "Status"}]},
                {"id": "invitees_table", "title": "Invitees", "source": "invitees", "icon": "users", "columns": [{"key": "name", "header": "Name"}, {"key": "email", "header": "Email"}]},
            ],
            "form": {
                "id": "cancel_form",
                "title": "Cancel booking",
                "page": "scheduled_events",
                "trigger": "cancel-booking",
                "submit_label": "Cancel",
                "fields": [
                    {"name": "uuid", "label": "Event uuid", "type": "text", "required": True},
                    {"name": "reason", "label": "Reason", "type": "text", "required": False},
                ],
            },
            "status": {"id": "events_status", "title": "Scheduled", "source": "scheduled_events", "label_field": "name"},
            "readme": _readme(
                "Calendly",
                "calendly-runtime",
                """## Connection / OAuth

Bearer OAuth (`auth.calendly.com`). Host typically `api.calendly.com`.

## CRM Automation examples

- `booking.created` → send confirmation, schedule reminder
- `booking.cancelled` → create follow-up task

## Webhooks

Signature header `Calendly-Webhook-Signature`. Calendly may use a timestamped scheme similar to Stripe — generic HMAC first, Runtime gap if the digest is not raw-body HMAC.
""",
            ),
        }
    )


def slack_app() -> None:
    conn = "slack"
    write_http_app(
        {
            "id": "slack-runtime",
            "name": "Slack",
            "description": "Channels, users, send message, and channel events as a metadata Marketplace App",
            "category": "collaboration",
            "tags": ["slack", "notifications", "runtime"],
            "comments": [
                "Slack — metadata Marketplace App (hosting: runtime).",
                "Staff notifications. No Slack Bolt app in this package.",
            ],
            "connection": {
                "id": conn,
                "auth_type": "bearer",
                "oauth": {
                    "authorize_url": "https://slack.com/oauth/v2/authorize",
                    "token_url": "https://slack.com/api/oauth.v2.access",
                    "revoke_url": "https://slack.com/api/auth.revoke",
                    "revoke_method": "POST",
                    "scopes": [
                        "channels:read",
                        "users:read",
                        "chat:write",
                        "channels:history",
                    ],
                },
                "webhooks": {
                    "hmac": {
                        "algorithm": "hmac-sha256",
                        "encoding": "hex",
                        "header": "X-Slack-Signature",
                        "key_source": "app_client",
                    },
                    "identity_header": "X-Slack-Team-Id",
                    "topic_header": "X-Slack-Event",
                    "event_id_header": "X-Slack-Request-Id",
                    "topics": {
                        "message.channels": "channel.message",
                        "channel_created": "channel.created",
                        "app_mention": "notification.created",
                    },
                },
            },
            "tools": [
                get_tool("list_channels", "Staff-only channel list", conn, "/api/conversations.list", items="channels", scopes=["channels:read"]),
                get_tool("list_users", "Staff-only user list", conn, "/api/users.list", items="members", scopes=["users:read"]),
                write_tool("send_message", "Staff-only send a channel message", conn, "POST", "/api/chat.postMessage", body={"channel": "{channel}", "text": "{text}"}, scopes=["chat:write"]),
                get_tool("get_channel_history", "Staff-only recent channel messages", conn, "/api/conversations.history", query={"channel": "{channel}"}, items="messages", scopes=["channels:history"]),
            ],
            "entities": [
                {"id": "channel", "name": "Channel", "description": "Slack channel", "fields": [field("name", "string", True), field("channel", "string")]},
                {"id": "slack_user", "name": "Slack user", "description": "Workspace user", "fields": [field("name", "string", True), field("email", "email")]},
                {"id": "slack_message", "name": "Message", "description": "Channel message", "fields": [field("channel", "string", True), field("text", "string", True)]},
            ],
            "flows": [
                {"id": "send-message", "name": "Send message", "description": "Post to Slack through generic Runtime HTTP", "tool": "send_message", "ask": {"field": "channel", "message": "Which channel id or name?"}, "extra_asks": [{"field": "text", "message": "What should we post?"}], "confirm": "Message sent to {{channel}}."},
                {"id": "list-channels", "name": "List channels", "description": "List Slack channels through generic Runtime HTTP", "tool": "list_channels", "confirm": "Here are the channels.\n{{items_text}}"},
                {"id": "list-users", "name": "List users", "description": "List Slack users through generic Runtime HTTP", "tool": "list_users", "confirm": "Here are the users.\n{{items_text}}"},
            ],
            "events": ["channel.message", "channel.created", "notification.created"],
            "triggers": [
                trigger("send_message", "send-message", "slack_message", ["send a slack message", "notify slack", "post to slack"], ["message sent"], ["channel", "text"], "Message sent to {{channel}}."),
                trigger("list_channels", "list-channels", "channel_list", ["list slack channels", "show channels"], ["channels"], [], "Here are the channels."),
                trigger("list_users", "list-users", "user_list", ["list slack users", "who is on slack"], ["users"], [], "Here are the users."),
            ],
            "slots": [
                slot("channel", ["channel", "channel id"], "string"),
                slot("text", ["message", "text", "notification"], "string"),
            ],
            "intro": "Metadata Marketplace App. Staff chat “notify slack” runs generic Runtime HTTP. Slack signing-secret v0 timestamped signatures are a generic Runtime capability gap if the header is not a raw HMAC.",
            "theme": {"primary": "#4a154b", "secondary": "#1d1c1d", "accent": "#36c5f0", "background": "#f8f8f8", "surface": "#ffffff", "text": "#1d1c1d"},
            "sources": [("channels", "channel"), ("users", "slack_user"), ("messages", "slack_message")],
            "tables": [
                {"id": "channels_table", "title": "Channels", "source": "channels", "icon": "list", "columns": [{"key": "name", "header": "Name"}]},
                {"id": "users_table", "title": "Users", "source": "users", "icon": "users", "columns": [{"key": "name", "header": "Name"}, {"key": "email", "header": "Email"}]},
                {"id": "messages_table", "title": "Messages", "source": "messages", "icon": "activity", "columns": [{"key": "channel", "header": "Channel"}, {"key": "text", "header": "Text"}]},
            ],
            "form": {
                "id": "message_form",
                "title": "Send message",
                "page": "messages",
                "trigger": "send-message",
                "submit_label": "Send",
                "fields": [
                    {"name": "channel", "label": "Channel", "type": "text", "required": True},
                    {"name": "text", "label": "Message", "type": "text", "required": True},
                ],
            },
            "readme": _readme(
                "Slack",
                "slack-runtime",
                """## Connection / OAuth

Bearer bot token from Slack OAuth v2. Scopes: `channels:read`, `users:read`, `chat:write`, `channels:history`.

Staff-only notifications. Surfaces are staff. Do not add channel-specific branches.

## CRM Automation examples

- `notification.created` → create CRM activity
- `channel.message` → optional staff digest

## Webhooks

`X-Slack-Signature` uses a `v0:` timestamped base string, not raw-body HMAC. Declare the header here; Runtime generic HMAC will not verify Slack's scheme until a generic signed-payload algorithm exists.
""",
            ),
        }
    )


def generate() -> None:
    freshdesk_app()
    zoho_crm_app()
    whatsapp_business_app()
    calendly_app()
    slack_app()


if __name__ == "__main__":
    generate()

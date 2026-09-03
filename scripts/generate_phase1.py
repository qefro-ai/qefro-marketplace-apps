"""Phase 1 system HTTP Marketplace Apps (metadata only)."""

from __future__ import annotations

from gen_lib import (
    enum_field,
    field,
    person_field,
    slot,
    trigger,
    write_http_app,
)
from http_tools import get_tool, owned_customer, write_tool

EMAIL_ALSO = [
    {
        "identity": "person.external_id",
        "paths": ["id", "customer", "customer.id", "customer_id"],
    },
    {
        "identity": "person.phone",
        "paths": ["phone", "customer.phone"],
    },
]


def _readme(title: str, app_id: str, body: str) -> str:
    return f"""# {app_id}

Metadata Marketplace App for {title}.

- **App id:** `{app_id}`
- **Hosting:** `runtime`
- **Execution:** generic HTTP tools against a workspace connection

There is no vendor SDK, webhook server, or API client in this package.
Credentials and destination host come from workspace Connect.

{body}
"""


def stripe_app() -> None:
    conn = "stripe"
    write_http_app(
        {
            "id": "stripe-runtime",
            "name": "Stripe",
            "description": "Customers, products, prices, payment links, checkout, invoices, subscriptions, payments, and refunds as a metadata Marketplace App",
            "category": "commerce",
            "tags": ["stripe", "payments", "runtime"],
            "comments": [
                "Stripe — metadata Marketplace App (hosting: runtime).",
                "No Stripe SDK, Connect client, or webhook server in this package.",
                "Workspace Connect supplies api.stripe.com and a Bearer credential.",
            ],
            "connection": {
                "_comments": [
                    "Workspace connection declaration. No host, secret key, or account id.",
                    "OAuth URLs are metadata for Qefro Runtime Stripe Connect; this package does not run OAuth.",
                    "Stripe-Signature is declared as generic HMAC metadata. Timestamped t=/v1= schemes need a generic Runtime algorithm.",
                ],
                "id": conn,
                "auth_type": "bearer",
                "oauth": {
                    "authorize_url": "https://connect.stripe.com/oauth/authorize",
                    "token_url": "https://connect.stripe.com/oauth/token",
                    "revoke_url": "https://connect.stripe.com/oauth/deauthorize",
                    "revoke_method": "POST",
                    "scopes": ["read_write"],
                },
                "webhooks": {
                    "hmac": {
                        "algorithm": "hmac-sha256",
                        "encoding": "hex",
                        "header": "Stripe-Signature",
                        "key_source": "app_client",
                    },
                    "identity_header": "Stripe-Account",
                    "topic_header": "Stripe-Event-Type",
                    "event_id_header": "Stripe-Event-Id",
                    "register_url": "https://{host}/v1/webhook_endpoints",
                    "topics": {
                        "customer.created": "customer.created",
                        "payment_intent.created": "payment.created",
                        "payment_intent.succeeded": "payment.succeeded",
                        "payment_intent.payment_failed": "payment.failed",
                        "charge.refunded": "refund.created",
                        "customer.subscription.created": "subscription.created",
                        "customer.subscription.updated": "subscription.updated",
                        "customer.subscription.deleted": "subscription.cancelled",
                        "invoice.paid": "invoice.paid",
                        "checkout.session.completed": "checkout.completed",
                    },
                },
            },
            "tools": [
                get_tool("list_customers", "Staff-only customer list on the workspace HTTP connection", conn, "/v1/customers", items="data", scopes=["read_write"]),
                get_tool("get_customer", "Staff-only customer fetch by Stripe id from a previous list", conn, "/v1/customers/{id}", item="customer", scopes=["read_write"], paginate=False),
                get_tool("list_my_customers", "List Stripe customers for the authenticated conversation Person only. Identity is resolved by the Runtime from Customer Hub; do not pass email, phone, person_id, or customer_id.", conn, "/v1/customers", items="data", query={"email": "{person.email}"}, scopes=["read_write"], staff=False, customer=owned_customer(["email"], also=EMAIL_ALSO)),
                get_tool("list_products", "List catalog products. Each item has an id for follow-up gets.", conn, "/v1/products", items="data", scopes=["read_write"], both=True, choice_id_prefix="product"),
                get_tool("get_product", "Get one catalog product by id from a previous list. Do not guess the id.", conn, "/v1/products/{id}", item="product", scopes=["read_write"], both=True, paginate=False),
                get_tool("list_prices", "Staff-only price list on the workspace HTTP connection", conn, "/v1/prices", items="data", scopes=["read_write"]),
                get_tool("list_payment_links", "Staff-only payment link list on the workspace HTTP connection", conn, "/v1/payment_links", items="data", scopes=["read_write"]),
                write_tool("create_payment_link", "Staff-only create a payment link for a price id", conn, "POST", "/v1/payment_links", body={"line_items": [{"price": "{price_id}", "quantity": "{quantity}"}]}, scopes=["read_write"]),
                write_tool("create_checkout_session", "Staff-only create a Checkout Session for a price id", conn, "POST", "/v1/checkout/sessions", body={"mode": "payment", "success_url": "{success_url}", "line_items": [{"price": "{price_id}", "quantity": "1"}]}, scopes=["read_write"]),
                get_tool("list_invoices", "Staff-only invoice list on the workspace HTTP connection", conn, "/v1/invoices", items="data", scopes=["read_write"]),
                get_tool("get_invoice", "Staff-only invoice fetch by id", conn, "/v1/invoices/{id}", item="invoice", scopes=["read_write"], paginate=False),
                get_tool("list_my_invoices", "List invoices for the authenticated Person using the Hub-mapped Stripe customer id. Do not pass customer_id or email.", conn, "/v1/invoices", items="data", query={"customer": "{person.external_id}"}, scopes=["read_write"], staff=False, customer=owned_customer(["customer_email", "customer.email"], require_any=["person.external_id"], collect=None, also=EMAIL_ALSO)),
                get_tool("list_subscriptions", "Staff-only subscription list on the workspace HTTP connection", conn, "/v1/subscriptions", items="data", scopes=["read_write"]),
                write_tool("create_subscription", "Staff-only create a subscription for an existing Stripe customer id and price id", conn, "POST", "/v1/subscriptions", body={"customer": "{stripe_customer}", "items": [{"price": "{price_id}"}]}, scopes=["read_write"]),
                get_tool("list_payments", "Staff-only PaymentIntent list on the workspace HTTP connection", conn, "/v1/payment_intents", items="data", scopes=["read_write"]),
                get_tool("get_payment", "Staff-only PaymentIntent fetch by id", conn, "/v1/payment_intents/{id}", item="payment_intent", scopes=["read_write"], paginate=False),
                write_tool("create_refund", "Staff-only refund a PaymentIntent", conn, "POST", "/v1/refunds", body={"payment_intent": "{payment_intent}"}, scopes=["read_write"]),
                get_tool("list_refunds", "Staff-only refund list on the workspace HTTP connection", conn, "/v1/refunds", items="data", scopes=["read_write"]),
            ],
            "entities": [
                {"id": "customer", "name": "Customer", "description": "Stripe customer bound to the platform Person model", "prefix": "C-", "fields": [field("name", "string", True), field("email", "email"), field("phone", "phone"), person_field("Existing Qefro Person identity (never a Stripe-local CRM)")]},
                {"id": "product", "name": "Product", "description": "Catalog product schema for staff UI", "prefix": "P-", "fields": [field("name", "string", True), field("description", "string"), enum_field("status", ["active", "inactive"])]},
                {"id": "price", "name": "Price", "description": "Price for a catalog product", "fields": [field("product_id", "string", True), field("unit_amount", "integer"), field("currency", "string")]},
                {"id": "payment_link", "name": "Payment link", "description": "Shareable Stripe payment link", "fields": [field("url", "url"), enum_field("status", ["active", "inactive"])]},
                {"id": "checkout_session", "name": "Checkout session", "description": "Checkout session schema for staff UI", "fields": [field("amount_total", "integer"), field("currency", "string"), enum_field("status", ["open", "complete", "expired"])]},
                {"id": "invoice", "name": "Invoice", "description": "Invoice bound to the platform Person model", "prefix": "I-", "fields": [field("number", "string"), field("amount_due", "integer"), field("customer_email", "email"), enum_field("status", ["draft", "open", "paid", "void", "uncollectible"]), person_field("Existing Qefro Person identity")]},
                {"id": "subscription", "name": "Subscription", "description": "Recurring subscription", "prefix": "S-", "fields": [field("customer_email", "email"), enum_field("status", ["incomplete", "active", "past_due", "canceled", "unpaid"]), person_field("Existing Qefro Person identity")]},
                {"id": "payment", "name": "Payment", "description": "PaymentIntent schema for staff UI", "prefix": "PAY-", "fields": [field("amount", "integer"), field("currency", "string"), enum_field("status", ["requires_payment_method", "requires_confirmation", "succeeded", "canceled"]), person_field("Existing Qefro Person identity")]},
                {"id": "refund", "name": "Refund", "description": "Refund against a payment", "fields": [field("amount", "integer"), field("payment_intent", "string"), enum_field("status", ["pending", "succeeded", "failed", "canceled"])]},
            ],
            "flows": [
                {"id": "create-payment-link", "name": "Create payment link", "description": "Create a Stripe payment link through generic Runtime HTTP", "tool": "create_payment_link", "ask": {"field": "price_id", "message": "Which Stripe price id should the link use?"}, "extra_asks": [{"field": "quantity", "message": "How many units?"}], "confirm": "Payment link created for {{price_id}}."},
                {"id": "create-subscription", "name": "Create subscription", "description": "Create a Stripe subscription through generic Runtime HTTP", "tool": "create_subscription", "ask": {"field": "stripe_customer", "message": "Which Stripe customer id should we subscribe?"}, "extra_asks": [{"field": "price_id", "message": "Which price id?"}], "confirm": "Subscription created for {{stripe_customer}}."},
                {"id": "refund-payment", "name": "Refund payment", "description": "Refund a PaymentIntent through generic Runtime HTTP", "tool": "create_refund", "ask": {"field": "payment_intent", "message": "Which PaymentIntent id should we refund?"}, "confirm": "Refund created for {{payment_intent}}."},
                {"id": "list-my-invoices", "name": "List my invoices", "description": "Show the authenticated customer's invoices through generic Runtime HTTP", "tool": "list_my_invoices", "confirm": "Here are your invoices.\n{{items_text}}"},
            ],
            "events": [
                "customer.created",
                "payment.created",
                "payment.succeeded",
                "payment.failed",
                "refund.created",
                "subscription.created",
                "subscription.updated",
                "subscription.cancelled",
                "invoice.paid",
                "checkout.completed",
            ],
            "triggers": [
                trigger("create_payment_link", "create-payment-link", "payment_link_input", ["create a payment link", "make a stripe link", "share a payment link"], ["payment link"], ["price_id"], "Payment link created for {{price_id}}."),
                trigger("create_subscription", "create-subscription", "subscription_input", ["create a subscription", "start a subscription"], ["subscription"], ["stripe_customer", "price_id"], "Subscription created for {{stripe_customer}}."),
                trigger("refund_payment", "refund-payment", "refund_input", ["refund a payment", "issue a refund"], ["refund"], ["payment_intent"], "Refund created for {{payment_intent}}."),
                trigger("list_my_invoices", "list-my-invoices", "my_invoice_list", ["show my invoices", "my invoices", "list my invoices"], ["your invoices"], [], "Here are your invoices."),
            ],
            "slots": [
                slot("price_id", ["price", "price id"], "string"),
                slot("quantity", ["quantity", "units"], "integer"),
                slot("stripe_customer", ["stripe customer", "customer id"], "string"),
                slot("payment_intent", ["payment", "payment intent"], "string"),
                slot("success_url", ["success url", "return url"], "string"),
            ],
            "intro": "Metadata Marketplace App. Chat “create a payment link” or “show my invoices” runs generic Runtime HTTP tools against the workspace Stripe connection (no SDK). Contacts stay on the existing Person CRM. Automations subscribe to payment.* events on the Automations host page.",
            "theme": {"primary": "#635bff", "secondary": "#0a2540", "accent": "#00d4ff", "background": "#f6f9fc", "surface": "#ffffff", "text": "#0a2540"},
            "sources": [("customers", "customer"), ("products", "product"), ("invoices", "invoice"), ("subscriptions", "subscription"), ("payments", "payment")],
            "tables": [
                {"id": "customers_table", "title": "Customers", "source": "customers", "icon": "users", "columns": [{"key": "name", "header": "Name"}, {"key": "email", "header": "Email"}]},
                {"id": "products_table", "title": "Products", "source": "products", "icon": "package", "columns": [{"key": "name", "header": "Name"}, {"key": "status", "header": "Status"}]},
                {"id": "invoices_table", "title": "Invoices", "source": "invoices", "icon": "receipt", "columns": [{"key": "number", "header": "Number"}, {"key": "amount_due", "header": "Due"}, {"key": "status", "header": "Status"}]},
                {"id": "subscriptions_table", "title": "Subscriptions", "source": "subscriptions", "icon": "credit-card", "columns": [{"key": "customer_email", "header": "Customer"}, {"key": "status", "header": "Status"}]},
                {"id": "payments_table", "title": "Payments", "source": "payments", "icon": "wallet", "columns": [{"key": "amount", "header": "Amount"}, {"key": "status", "header": "Status"}]},
            ],
            "form": {
                "id": "payment_link_form",
                "title": "Create payment link",
                "page": "products",
                "trigger": "create-payment-link",
                "submit_label": "Create link",
                "fields": [
                    {"name": "price_id", "label": "Price id", "type": "text", "required": True},
                    {"name": "quantity", "label": "Quantity", "type": "number", "required": True},
                ],
            },
            "status": {"id": "payments_status", "title": "Payments", "source": "payments", "label_field": "amount", "empty_title": "No payments yet"},
            "readme": _readme(
                "Stripe",
                "stripe-runtime",
                """## Connection

Workspace Connect supplies the allowlisted host (typically `api.stripe.com`) and a Bearer secret key, or Stripe Connect OAuth using the declared authorize/token URLs. Required OAuth scope: `read_write`.

## CRM Automation examples

Configure on the Automations host page. This package emits events; it does not run automations inline.

- `payment.succeeded` → update CRM relationship, send confirmation
- `payment.failed` → create follow-up task
- `subscription.cancelled` → create customer retention task
- `refund.created` → notify staff

## Webhooks

HMAC header `Stripe-Signature`, identity header `Stripe-Account`, topic header `Stripe-Event-Type`, idempotency header `Stripe-Event-Id`. Runtime verifies the raw body. Stripe's timestamped `t=,v1=` signature format is a generic Runtime capability gap if the header is not a raw HMAC digest.
""",
            ),
        }
    )


def razorpay_app() -> None:
    conn = "razorpay"
    write_http_app(
        {
            "id": "razorpay-runtime",
            "name": "Razorpay",
            "description": "Customers, orders, payments, refunds, invoices, and payment links as a metadata Marketplace App",
            "category": "commerce",
            "tags": ["razorpay", "payments", "runtime"],
            "comments": [
                "Razorpay — metadata Marketplace App (hosting: runtime).",
                "No Razorpay SDK or webhook server. Workspace supplies host and Basic/named-header credentials.",
            ],
            "connection": {
                "_comments": [
                    "Workspace stores Key Id:Key Secret as the named Authorization header value (Basic).",
                    "No host or secrets in this file.",
                ],
                "id": conn,
                "auth_type": "named_header",
                "auth_header": "Authorization",
                "webhooks": {
                    "hmac": {
                        "algorithm": "hmac-sha256",
                        "encoding": "hex",
                        "header": "X-Razorpay-Signature",
                        "key_source": "app_client",
                    },
                    "identity_header": "X-Razorpay-Account",
                    "topic_header": "X-Razorpay-Event",
                    "event_id_header": "X-Razorpay-Event-Id",
                    "topics": {
                        "order.paid": "order.paid",
                        "payment.authorized": "payment.created",
                        "payment.captured": "payment.succeeded",
                        "payment.failed": "payment.failed",
                        "refund.created": "refund.created",
                        "invoice.paid": "invoice.paid",
                    },
                },
            },
            "tools": [
                get_tool("list_customers", "Staff-only customer list on the workspace HTTP connection", conn, "/v1/customers", items="items"),
                get_tool("get_customer", "Staff-only customer fetch by id", conn, "/v1/customers/{id}", paginate=False),
                get_tool("list_my_customers", "List Razorpay customers for the authenticated conversation Person only. Do not pass email, phone, person_id, or customer_id.", conn, "/v1/customers", items="items", query={"email": "{person.email}"}, staff=False, customer=owned_customer(["email"], also=EMAIL_ALSO)),
                get_tool("list_orders", "Staff-only order list on the workspace HTTP connection", conn, "/v1/orders", items="items"),
                get_tool("get_order", "Staff-only order fetch by id", conn, "/v1/orders/{id}", paginate=False),
                write_tool("create_order", "Staff-only create a Razorpay order", conn, "POST", "/v1/orders", body={"amount": "{amount}", "currency": "{currency}"}),
                get_tool("list_payments", "Staff-only payment list on the workspace HTTP connection", conn, "/v1/payments", items="items"),
                get_tool("get_payment", "Staff-only payment fetch by id", conn, "/v1/payments/{id}", paginate=False),
                write_tool("create_refund", "Staff-only refund a payment", conn, "POST", "/v1/payments/{id}/refund", body={"amount": "{amount}"}),
                get_tool("list_invoices", "Staff-only invoice list on the workspace HTTP connection", conn, "/v1/invoices", items="items"),
                get_tool("list_payment_links", "Staff-only payment link list on the workspace HTTP connection", conn, "/v1/payment_links", items="payment_links"),
                write_tool("create_payment_link", "Staff-only create a payment link", conn, "POST", "/v1/payment_links", body={"amount": "{amount}", "currency": "{currency}", "description": "{description}"}),
            ],
            "entities": [
                {"id": "customer", "name": "Customer", "description": "Razorpay customer bound to Person", "prefix": "C-", "fields": [field("name", "string", True), field("email", "email"), field("phone", "phone"), person_field("Existing Qefro Person identity")]},
                {"id": "order", "name": "Order", "description": "Razorpay order", "prefix": "O-", "fields": [field("amount", "integer", True), field("currency", "string"), enum_field("status", ["created", "attempted", "paid"]), person_field("Existing Qefro Person identity")]},
                {"id": "payment", "name": "Payment", "description": "Captured or authorized payment", "fields": [field("amount", "integer"), enum_field("status", ["created", "authorized", "captured", "failed"])]},
                {"id": "refund", "name": "Refund", "description": "Refund against a payment", "fields": [field("amount", "integer"), enum_field("status", ["pending", "processed", "failed"])]},
                {"id": "invoice", "name": "Invoice", "description": "Razorpay invoice", "fields": [field("amount", "integer"), field("customer_email", "email"), enum_field("status", ["draft", "issued", "paid", "cancelled"])]},
                {"id": "payment_link", "name": "Payment link", "description": "Shareable payment link", "fields": [field("amount", "integer"), field("description", "string"), enum_field("status", ["created", "paid", "expired"])]},
            ],
            "flows": [
                {"id": "create-order", "name": "Create order", "description": "Create a Razorpay order through generic Runtime HTTP", "tool": "create_order", "ask": {"field": "amount", "message": "What amount should we charge (smallest currency unit)?"}, "extra_asks": [{"field": "currency", "message": "Which currency code?"}], "confirm": "Order created for {{amount}} {{currency}}."},
                {"id": "refund-payment", "name": "Refund payment", "description": "Refund a Razorpay payment through generic Runtime HTTP", "tool": "create_refund", "ask": {"field": "id", "message": "Which payment id should we refund?"}, "extra_asks": [{"field": "amount", "message": "Refund amount in the smallest currency unit?"}], "confirm": "Refund created for payment {{id}}."},
                {"id": "create-payment-link", "name": "Create payment link", "description": "Create a Razorpay payment link through generic Runtime HTTP", "tool": "create_payment_link", "ask": {"field": "amount", "message": "What amount should the link charge?"}, "extra_asks": [{"field": "currency", "message": "Which currency code?"}, {"field": "description", "message": "Short description for the link?"}], "confirm": "Payment link created for {{amount}} {{currency}}."},
                {"id": "list-my-customers", "name": "Find my customer record", "description": "Show the authenticated customer's Razorpay customer records", "tool": "list_my_customers", "confirm": "Here is your customer record.\n{{items_text}}"},
            ],
            "events": ["order.paid", "payment.created", "payment.succeeded", "payment.failed", "refund.created", "invoice.paid"],
            "triggers": [
                trigger("create_order", "create-order", "order_input", ["create a razorpay order", "create an order"], ["order"], ["amount"], "Order created for {{amount}} {{currency}}."),
                trigger("refund_payment", "refund-payment", "refund_input", ["refund a razorpay payment", "issue a refund"], ["refund"], ["id"], "Refund created for payment {{id}}."),
                trigger("create_payment_link", "create-payment-link", "payment_link_input", ["create a payment link", "share a payment link"], ["payment link"], ["amount"], "Payment link created for {{amount}} {{currency}}."),
                trigger("list_my_customers", "list-my-customers", "my_customer_list", ["find my razorpay customer", "my customer record"], ["your customer"], [], "Here is your customer record."),
            ],
            "slots": [
                slot("amount", ["amount", "rupees", "paise"], "integer"),
                slot("currency", ["currency", "INR"], "string"),
                slot("id", ["payment id", "payment"], "string"),
                slot("description", ["description", "note"], "string"),
            ],
            "intro": "Metadata Marketplace App. Chat “create a payment link” runs generic Runtime HTTP against the workspace Razorpay connection. Contacts stay on Person CRM. Automations subscribe to payment.* events.",
            "theme": {"primary": "#0b72e7", "secondary": "#0f172a", "accent": "#3395ff", "background": "#f8fafc", "surface": "#ffffff", "text": "#0f172a"},
            "sources": [("customers", "customer"), ("orders", "order"), ("payments", "payment"), ("invoices", "invoice")],
            "tables": [
                {"id": "customers_table", "title": "Customers", "source": "customers", "icon": "users", "columns": [{"key": "name", "header": "Name"}, {"key": "email", "header": "Email"}]},
                {"id": "orders_table", "title": "Orders", "source": "orders", "icon": "receipt", "columns": [{"key": "amount", "header": "Amount"}, {"key": "status", "header": "Status"}]},
                {"id": "payments_table", "title": "Payments", "source": "payments", "icon": "credit-card", "columns": [{"key": "amount", "header": "Amount"}, {"key": "status", "header": "Status"}]},
                {"id": "invoices_table", "title": "Invoices", "source": "invoices", "icon": "file-text", "columns": [{"key": "amount", "header": "Amount"}, {"key": "status", "header": "Status"}]},
            ],
            "form": {
                "id": "order_form",
                "title": "Create order",
                "page": "orders",
                "trigger": "create-order",
                "submit_label": "Create order",
                "fields": [
                    {"name": "amount", "label": "Amount", "type": "number", "required": True},
                    {"name": "currency", "label": "Currency", "type": "text", "required": True},
                ],
            },
            "status": {"id": "orders_status", "title": "Orders", "source": "orders", "label_field": "amount"},
            "readme": _readme(
                "Razorpay",
                "razorpay-runtime",
                """## Connection

Named header `Authorization` (workspace stores Basic credentials). Host is typically `api.razorpay.com`.

## CRM Automation examples

- `payment.succeeded` → update CRM relationship, send confirmation
- `payment.failed` → create follow-up task
- `order.paid` → notify staff

## Webhooks

`X-Razorpay-Signature` HMAC-SHA256 hex of the raw body. Identity `X-Razorpay-Account`, topic `X-Razorpay-Event`, idempotency `X-Razorpay-Event-Id`. If Razorpay omits those identity/topic headers, Runtime needs a generic JSON-body topic mapping capability.
""",
            ),
        }
    )


def woocommerce_app() -> None:
    conn = "woocommerce"
    write_http_app(
        {
            "id": "woocommerce-runtime",
            "name": "WooCommerce",
            "description": "Products, customers, orders, coupons, categories, and inventory as a metadata Marketplace App",
            "category": "commerce",
            "tags": ["woocommerce", "commerce", "runtime"],
            "comments": [
                "WooCommerce — metadata Marketplace App (hosting: runtime).",
                "Generic HTTP against the workspace store host. No WooCommerce plugin or SDK in this package.",
            ],
            "connection": {
                "_comments": [
                    "Workspace supplies the store host and REST credentials (named Authorization header).",
                    "No store URL or consumer secret in this file.",
                ],
                "id": conn,
                "auth_type": "named_header",
                "auth_header": "Authorization",
                "webhooks": {
                    "hmac": {
                        "algorithm": "hmac-sha256",
                        "encoding": "base64",
                        "header": "X-WC-Webhook-Signature",
                        "key_source": "app_client",
                    },
                    "identity_header": "X-WC-Webhook-Source",
                    "topic_header": "X-WC-Webhook-Topic",
                    "event_id_header": "X-WC-Webhook-ID",
                    "register_url": "https://{host}/wp-json/wc/v3/webhooks",
                    "topics": {
                        "order.created": "order.created",
                        "order.updated": "order.updated",
                        "order.deleted": "order.cancelled",
                        "customer.created": "customer.created",
                        "product.updated": "product.updated",
                        "coupon.created": "coupon.created",
                    },
                },
            },
            "tools": [
                get_tool("search_products", "Search the catalog when the customer names a product. Pass that text as query.", conn, "/wp-json/wc/v3/products", items="products", query={"search": "{query}"}, both=True, limit_param="per_page", choice_id_prefix="product"),
                get_tool("list_products", "Staff-only product list on the workspace HTTP connection", conn, "/wp-json/wc/v3/products", items="products", limit_param="per_page"),
                get_tool("get_product", "Get one catalog product by id from a previous list. Do not guess the id.", conn, "/wp-json/wc/v3/products/{id}", both=True, paginate=False),
                write_tool("update_inventory", "Staff-only update product stock quantity", conn, "PUT", "/wp-json/wc/v3/products/{id}", body={"stock_quantity": "{stock_quantity}", "manage_stock": True}),
                get_tool("list_customers", "Staff-only customer list on the workspace HTTP connection", conn, "/wp-json/wc/v3/customers", items="customers", limit_param="per_page"),
                get_tool("get_customer", "Staff-only customer fetch by id", conn, "/wp-json/wc/v3/customers/{id}", paginate=False),
                get_tool("list_orders", "Staff-only shop-wide order list on the workspace HTTP connection", conn, "/wp-json/wc/v3/orders", items="orders", limit_param="per_page"),
                get_tool("get_order", "Staff-only order fetch by id", conn, "/wp-json/wc/v3/orders/{id}", paginate=False),
                get_tool("list_my_orders", "List orders for the authenticated conversation Person only. Identity is resolved by the Runtime from Customer Hub; do not pass email, phone, person_id, or customer_id.", conn, "/wp-json/wc/v3/orders", items="orders", query={"customer_email": "{person.email}"}, staff=False, customer=owned_customer(["billing.email", "email"], also=[{"identity": "person.external_id", "paths": ["customer_id"]}, {"identity": "person.phone", "paths": ["billing.phone"]}]), limit_param="per_page"),
                get_tool("get_my_order", "Look up one order by id for the authenticated conversation Person. The order id may come from the user; identity must not.", conn, "/wp-json/wc/v3/orders/{id}", query={"customer_email": "{person.email}"}, staff=False, customer=owned_customer(["billing.email", "email"], also=[{"identity": "person.external_id", "paths": ["customer_id"]}]), paginate=False),
                get_tool("list_coupons", "Staff-only coupon list on the workspace HTTP connection", conn, "/wp-json/wc/v3/coupons", items="coupons", limit_param="per_page"),
                get_tool("list_categories", "List product categories", conn, "/wp-json/wc/v3/products/categories", items="categories", both=True, limit_param="per_page"),
            ],
            "entities": [
                {"id": "product", "name": "Product", "description": "Catalog product", "prefix": "P-", "fields": [field("name", "string", True), field("sku", "string"), field("price", "float"), field("stock_quantity", "integer"), enum_field("status", ["draft", "publish", "private"])]},
                {"id": "customer", "name": "Customer", "description": "Store customer bound to Person", "prefix": "C-", "fields": [field("name", "string", True), field("email", "email"), field("phone", "phone"), person_field("Existing Qefro Person identity")]},
                {"id": "order", "name": "Order", "description": "Customer order", "prefix": "O-", "fields": [field("total", "float"), field("currency", "string"), enum_field("status", ["pending", "processing", "on-hold", "completed", "cancelled", "refunded", "failed"]), person_field("Existing Qefro Person identity")]},
                {"id": "coupon", "name": "Coupon", "description": "Discount coupon", "fields": [field("code", "string", True), field("amount", "string"), enum_field("status", ["publish", "draft"])]},
                {"id": "category", "name": "Category", "description": "Product category", "fields": [field("name", "string", True), field("slug", "string")]},
            ],
            "flows": [
                {"id": "search-products", "name": "Search products", "description": "Find catalog products through generic Runtime HTTP", "tool": "search_products", "ask": {"field": "query", "message": "What product are you looking for?"}, "confirm": "Products matching {{query}}.\n{{items_text}}"},
                {"id": "get-customer-orders", "name": "Get customer orders", "description": "Show the authenticated customer's own orders", "tool": "list_my_orders", "confirm": "Here are your recent orders.\n{{items_text}}"},
                {"id": "get-order", "name": "Get my order", "description": "Look up one order for the authenticated Person", "tool": "get_my_order", "ask": {"field": "id", "message": "What is the order id?"}, "confirm": "Here is that order.\n{{items_text}}"},
                {"id": "update-inventory", "name": "Update inventory", "description": "Staff stock update through generic Runtime HTTP", "tool": "update_inventory", "ask": {"field": "id", "message": "Which product id should we update?"}, "extra_asks": [{"field": "stock_quantity", "message": "What is the new stock quantity?"}], "confirm": "Inventory updated for product {{id}}."},
            ],
            "events": ["order.created", "order.updated", "order.cancelled", "customer.created", "product.updated", "coupon.created"],
            "triggers": [
                trigger("search_products", "search-products", "product_query", ["find a product", "search products", "search the catalog"], ["products matching"], ["query"], "Products matching {{query}}."),
                trigger("list_my_orders", "get-customer-orders", "my_order_list", ["show my recent orders", "my orders", "where is my order"], ["your recent orders"], [], "Here are your recent orders."),
                trigger("get_my_order", "get-order", "order_id", ["status of order", "look up order"], ["that order"], ["id"], "Here is that order."),
                trigger("update_inventory", "update-inventory", "inventory_input", ["update stock", "update inventory"], ["inventory updated"], ["id", "stock_quantity"], "Inventory updated for product {{id}}."),
            ],
            "slots": [
                slot("query", ["product", "search", "find", "catalog"], "string"),
                slot("id", ["order", "order id", "product id"], "string"),
                slot("stock_quantity", ["stock", "quantity", "inventory"], "integer"),
            ],
            "intro": "Metadata Marketplace App. Chat “find black shoes” or “show my recent orders” runs generic Runtime HTTP against the workspace WooCommerce connection. Contacts stay on Person CRM.",
            "theme": {"primary": "#7f54b3", "secondary": "#201c1c", "accent": "#9b6cc3", "background": "#f6f6f6", "surface": "#ffffff", "text": "#201c1c"},
            "sources": [("products", "product"), ("customers", "customer"), ("orders", "order"), ("coupons", "coupon")],
            "tables": [
                {"id": "products_table", "title": "Products", "source": "products", "icon": "package", "columns": [{"key": "name", "header": "Name"}, {"key": "price", "header": "Price"}, {"key": "stock_quantity", "header": "Stock"}]},
                {"id": "customers_table", "title": "Customers", "source": "customers", "icon": "users", "columns": [{"key": "name", "header": "Name"}, {"key": "email", "header": "Email"}]},
                {"id": "orders_table", "title": "Orders", "source": "orders", "icon": "receipt", "columns": [{"key": "total", "header": "Total"}, {"key": "status", "header": "Status"}]},
                {"id": "coupons_table", "title": "Coupons", "source": "coupons", "icon": "wallet", "columns": [{"key": "code", "header": "Code"}, {"key": "amount", "header": "Amount"}]},
            ],
            "form": {
                "id": "product_search",
                "title": "Search products",
                "page": "products",
                "trigger": "search-products",
                "submit_label": "Search",
                "fields": [{"name": "query", "label": "Search", "type": "text", "required": True}],
            },
            "status": {"id": "orders_status", "title": "Orders", "source": "orders", "label_field": "total"},
            "readme": _readme(
                "WooCommerce",
                "woocommerce-runtime",
                """## Connection

Workspace supplies the store host and REST credentials as `Authorization`. Paths are `/wp-json/wc/v3/...`.

## CRM Automation examples

- `order.created` → send confirmation, create CRM activity
- `order.cancelled` → create customer follow-up task
- `customer.created` → bind Person relationship
- `product.updated` → notify staff of inventory change

## Webhooks

`X-WC-Webhook-Signature` base64 HMAC-SHA256, source `X-WC-Webhook-Source`, topic `X-WC-Webhook-Topic`, id `X-WC-Webhook-ID`.
""",
            ),
        }
    )


def google_calendar_app() -> None:
    conn = "google-calendar"
    write_http_app(
        {
            "id": "google-calendar-runtime",
            "name": "Google Calendar",
            "description": "Calendars, events, scheduling, and free-busy as a metadata Marketplace App",
            "category": "productivity",
            "tags": ["google", "calendar", "runtime"],
            "comments": [
                "Google Calendar — metadata Marketplace App (hosting: runtime).",
                "OAuth and HTTP are executed by Qefro Runtime. This package has no Google client.",
            ],
            "connection": {
                "_comments": [
                    "Workspace OAuth supplies tokens. Host is typically www.googleapis.com.",
                    "No client secret in this file.",
                ],
                "id": conn,
                "auth_type": "bearer",
                "oauth": {
                    "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                    "token_url": "https://oauth2.googleapis.com/token",
                    "revoke_url": "https://oauth2.googleapis.com/revoke",
                    "revoke_method": "POST",
                    "scopes": [
                        "https://www.googleapis.com/auth/calendar",
                        "https://www.googleapis.com/auth/calendar.events",
                    ],
                },
                "webhooks": {
                    "hmac": {
                        "algorithm": "hmac-sha256",
                        "encoding": "hex",
                        "header": "X-Goog-Channel-Token",
                        "key_source": "app_client",
                    },
                    "identity_header": "X-Goog-Channel-ID",
                    "topic_header": "X-Goog-Resource-State",
                    "event_id_header": "X-Goog-Message-Number",
                    "topics": {
                        "exists": "event.updated",
                        "sync": "event.created",
                        "not_exists": "event.cancelled",
                    },
                },
            },
            "tools": [
                get_tool("list_calendars", "Staff-only calendar list for the connected Google account", conn, "/calendar/v3/users/me/calendarList", items="items", scopes=["https://www.googleapis.com/auth/calendar"]),
                get_tool("list_events", "Staff-only list events on a calendar", conn, "/calendar/v3/calendars/{calendar_id}/events", items="items", scopes=["https://www.googleapis.com/auth/calendar.events"], limit_param="maxResults"),
                get_tool("get_event", "Staff-only fetch one event", conn, "/calendar/v3/calendars/{calendar_id}/events/{event_id}", paginate=False, scopes=["https://www.googleapis.com/auth/calendar.events"]),
                write_tool("create_event", "Staff-only create a calendar event", conn, "POST", "/calendar/v3/calendars/{calendar_id}/events", body={"summary": "{summary}", "start": {"dateTime": "{start}"}, "end": {"dateTime": "{end}"}}, scopes=["https://www.googleapis.com/auth/calendar.events"]),
                write_tool("update_event", "Staff-only update a calendar event", conn, "PATCH", "/calendar/v3/calendars/{calendar_id}/events/{event_id}", body={"summary": "{summary}", "start": {"dateTime": "{start}"}, "end": {"dateTime": "{end}"}}, scopes=["https://www.googleapis.com/auth/calendar.events"]),
                write_tool("cancel_event", "Staff-only cancel a calendar event", conn, "DELETE", "/calendar/v3/calendars/{calendar_id}/events/{event_id}", scopes=["https://www.googleapis.com/auth/calendar.events"]),
                write_tool("query_freebusy", "Staff-only free-busy query", conn, "POST", "/calendar/v3/freeBusy", body={"timeMin": "{start}", "timeMax": "{end}", "items": [{"id": "{calendar_id}"}]}, scopes=["https://www.googleapis.com/auth/calendar"]),
            ],
            "entities": [
                {"id": "calendar", "name": "Calendar", "description": "Google calendar", "fields": [field("summary", "string", True), field("time_zone", "string")]},
                {"id": "event", "name": "Event", "description": "Calendar event", "prefix": "E-", "fields": [field("summary", "string", True), field("start", "datetime"), field("end", "datetime"), enum_field("status", ["confirmed", "tentative", "cancelled"]), person_field("Existing Qefro Person identity")]},
            ],
            "flows": [
                {"id": "schedule-appointment", "name": "Schedule appointment", "description": "Create a calendar event through generic Runtime HTTP", "tool": "create_event", "ask": {"field": "calendar_id", "message": "Which calendar id should we use? Use primary if unsure."}, "extra_asks": [{"field": "summary", "message": "What is the event title?"}, {"field": "start", "message": "When does it start (RFC3339)?"}, {"field": "end", "message": "When does it end (RFC3339)?"}], "confirm": "Event {{summary}} scheduled."},
                {"id": "reschedule-event", "name": "Reschedule event", "description": "Update a calendar event through generic Runtime HTTP", "tool": "update_event", "ask": {"field": "calendar_id", "message": "Which calendar id?"}, "extra_asks": [{"field": "event_id", "message": "Which event id?"}, {"field": "summary", "message": "Updated title?"}, {"field": "start", "message": "New start (RFC3339)?"}, {"field": "end", "message": "New end (RFC3339)?"}], "confirm": "Event {{event_id}} rescheduled."},
                {"id": "cancel-event", "name": "Cancel event", "description": "Cancel a calendar event through generic Runtime HTTP", "tool": "cancel_event", "ask": {"field": "calendar_id", "message": "Which calendar id?"}, "extra_asks": [{"field": "event_id", "message": "Which event id should we cancel?"}], "confirm": "Event {{event_id}} cancelled."},
                {"id": "check-availability", "name": "Check availability", "description": "Free-busy query through generic Runtime HTTP", "tool": "query_freebusy", "ask": {"field": "calendar_id", "message": "Which calendar id?"}, "extra_asks": [{"field": "start", "message": "Window start (RFC3339)?"}, {"field": "end", "message": "Window end (RFC3339)?"}], "confirm": "Availability for {{calendar_id}}."},
            ],
            "events": ["event.created", "event.updated", "event.cancelled", "booking.created"],
            "triggers": [
                trigger("schedule_appointment", "schedule-appointment", "event_input", ["schedule an appointment", "create a calendar event", "book a meeting"], ["scheduled"], ["summary", "start"], "Event {{summary}} scheduled."),
                trigger("reschedule_event", "reschedule-event", "reschedule_input", ["reschedule the event", "move the meeting"], ["rescheduled"], ["event_id"], "Event {{event_id}} rescheduled."),
                trigger("cancel_event", "cancel-event", "cancel_input", ["cancel the event", "delete the meeting"], ["cancelled"], ["event_id"], "Event {{event_id}} cancelled."),
                trigger("check_availability", "check-availability", "freebusy_input", ["check availability", "am I free", "free busy"], ["availability"], ["calendar_id"], "Availability for {{calendar_id}}."),
            ],
            "slots": [
                slot("calendar_id", ["calendar", "calendar id", "primary"], "string"),
                slot("event_id", ["event", "event id"], "string"),
                slot("summary", ["title", "summary", "event name"], "string"),
                slot("start", ["start", "from"], "string"),
                slot("end", ["end", "until"], "string"),
            ],
            "intro": "Metadata Marketplace App. Staff chat “schedule an appointment” runs generic Runtime HTTP against the workspace Google Calendar connection. Customer Hub identity is not the Google account — these tools are staff-only.",
            "theme": {"primary": "#1a73e8", "secondary": "#202124", "accent": "#34a853", "background": "#f8f9fa", "surface": "#ffffff", "text": "#202124"},
            "sources": [("calendars", "calendar"), ("events", "event")],
            "tables": [
                {"id": "calendars_table", "title": "Calendars", "source": "calendars", "icon": "calendar", "columns": [{"key": "summary", "header": "Name"}, {"key": "time_zone", "header": "Timezone"}]},
                {"id": "events_table", "title": "Events", "source": "events", "icon": "clock", "columns": [{"key": "summary", "header": "Title"}, {"key": "start", "header": "Start"}, {"key": "status", "header": "Status"}]},
            ],
            "form": {
                "id": "event_form",
                "title": "Schedule event",
                "page": "events",
                "trigger": "schedule-appointment",
                "submit_label": "Create event",
                "fields": [
                    {"name": "calendar_id", "label": "Calendar id", "type": "text", "required": True},
                    {"name": "summary", "label": "Title", "type": "text", "required": True},
                    {"name": "start", "label": "Start", "type": "text", "required": True},
                    {"name": "end", "label": "End", "type": "text", "required": True},
                ],
            },
            "status": {"id": "events_status", "title": "Events", "source": "events", "label_field": "summary"},
            "readme": _readme(
                "Google Calendar",
                "google-calendar-runtime",
                """## Connection / OAuth

Bearer tokens from Google OAuth. Scopes: `calendar` and `calendar.events`. Host typically `www.googleapis.com`.

Staff-only: the connected Google account is not Customer Hub Person identity.

## CRM Automation examples

- `event.created` / `booking.created` → send confirmation, schedule reminder
- `event.cancelled` → create follow-up task

## Webhooks

Google push notifications use channel headers (`X-Goog-Channel-ID`, `X-Goog-Resource-State`). HMAC over raw body may not match Google's channel token model — generic signed-channel verification is a Runtime gap.
""",
            ),
        }
    )


def google_sheets_app() -> None:
    conn = "google-sheets"
    write_http_app(
        {
            "id": "google-sheets-runtime",
            "name": "Google Sheets",
            "description": "Spreadsheets, sheets, and row read/append/update as a metadata Marketplace App",
            "category": "productivity",
            "tags": ["google", "sheets", "runtime"],
            "comments": [
                "Google Sheets — metadata Marketplace App (hosting: runtime).",
                "No Google client in this package.",
            ],
            "connection": {
                "_comments": [
                    "Workspace OAuth supplies tokens. Host is typically sheets.googleapis.com.",
                ],
                "id": conn,
                "auth_type": "bearer",
                "oauth": {
                    "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                    "token_url": "https://oauth2.googleapis.com/token",
                    "revoke_url": "https://oauth2.googleapis.com/revoke",
                    "revoke_method": "POST",
                    "scopes": [
                        "https://www.googleapis.com/auth/spreadsheets",
                        "https://www.googleapis.com/auth/spreadsheets.readonly",
                    ],
                },
            },
            "tools": [
                get_tool("get_spreadsheet", "Staff-only fetch spreadsheet metadata including sheets", conn, "/v4/spreadsheets/{spreadsheet_id}", paginate=False, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]),
                get_tool("read_rows", "Staff-only read cell values from a range", conn, "/v4/spreadsheets/{spreadsheet_id}/values/{range}", paginate=False, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]),
                write_tool("append_rows", "Staff-only append rows to a range", conn, "POST", "/v4/spreadsheets/{spreadsheet_id}/values/{range}:append", query={"valueInputOption": "USER_ENTERED"}, body={"values": [["{col1}", "{col2}", "{col3}"]]}, scopes=["https://www.googleapis.com/auth/spreadsheets"]),
                write_tool("update_rows", "Staff-only update rows in a range", conn, "PUT", "/v4/spreadsheets/{spreadsheet_id}/values/{range}", query={"valueInputOption": "USER_ENTERED"}, body={"values": [["{col1}", "{col2}", "{col3}"]]}, scopes=["https://www.googleapis.com/auth/spreadsheets"]),
            ],
            "entities": [
                {"id": "spreadsheet", "name": "Spreadsheet", "description": "Google spreadsheet", "fields": [field("title", "string", True), field("spreadsheet_id", "string")]},
                {"id": "sheet", "name": "Sheet", "description": "Tab inside a spreadsheet", "fields": [field("title", "string", True), field("sheet_id", "string")]},
                {"id": "row", "name": "Row", "description": "Row values for staff UI", "fields": [field("col1", "string"), field("col2", "string"), field("col3", "string")]},
            ],
            "flows": [
                {"id": "read-rows", "name": "Read rows", "description": "Read a sheet range through generic Runtime HTTP", "tool": "read_rows", "ask": {"field": "spreadsheet_id", "message": "What is the spreadsheet id?"}, "extra_asks": [{"field": "range", "message": "Which A1 range should we read?"}], "confirm": "Rows from {{range}}."},
                {"id": "append-rows", "name": "Append rows", "description": "Append a row through generic Runtime HTTP", "tool": "append_rows", "ask": {"field": "spreadsheet_id", "message": "What is the spreadsheet id?"}, "extra_asks": [{"field": "range", "message": "Which range should we append to?"}, {"field": "col1", "message": "Value for column 1?"}, {"field": "col2", "message": "Value for column 2?"}, {"field": "col3", "message": "Value for column 3?"}], "confirm": "Row appended to {{range}}."},
                {"id": "update-rows", "name": "Update rows", "description": "Update a sheet range through generic Runtime HTTP", "tool": "update_rows", "ask": {"field": "spreadsheet_id", "message": "What is the spreadsheet id?"}, "extra_asks": [{"field": "range", "message": "Which range should we update?"}, {"field": "col1", "message": "Value for column 1?"}, {"field": "col2", "message": "Value for column 2?"}, {"field": "col3", "message": "Value for column 3?"}], "confirm": "Range {{range}} updated."},
            ],
            "events": ["spreadsheet.updated", "row.appended", "row.updated"],
            "triggers": [
                trigger("read_rows", "read-rows", "read_input", ["read the sheet", "show spreadsheet rows"], ["rows"], ["spreadsheet_id", "range"], "Rows from {{range}}."),
                trigger("append_rows", "append-rows", "append_input", ["append a row", "add a sheet row"], ["appended"], ["spreadsheet_id", "range"], "Row appended to {{range}}."),
                trigger("update_rows", "update-rows", "update_input", ["update the sheet", "change spreadsheet rows"], ["updated"], ["spreadsheet_id", "range"], "Range {{range}} updated."),
            ],
            "slots": [
                slot("spreadsheet_id", ["spreadsheet", "sheet id"], "string"),
                slot("range", ["range", "a1"], "string"),
                slot("col1", ["column 1", "first value"], "string"),
                slot("col2", ["column 2", "second value"], "string"),
                slot("col3", ["column 3", "third value"], "string"),
            ],
            "intro": "Metadata Marketplace App. Staff chat “append a row” runs generic Runtime HTTP against the workspace Google Sheets connection. Staff-only — Customer Hub is not the Google account.",
            "theme": {"primary": "#0f9d58", "secondary": "#188038", "accent": "#34a853", "background": "#f8f9fa", "surface": "#ffffff", "text": "#202124"},
            "sources": [("spreadsheets", "spreadsheet"), ("sheets", "sheet"), ("rows", "row")],
            "tables": [
                {"id": "spreadsheets_table", "title": "Spreadsheets", "source": "spreadsheets", "icon": "file-text", "columns": [{"key": "title", "header": "Title"}]},
                {"id": "sheets_table", "title": "Sheets", "source": "sheets", "icon": "list", "columns": [{"key": "title", "header": "Tab"}]},
                {"id": "rows_table", "title": "Rows", "source": "rows", "icon": "clipboard", "columns": [{"key": "col1", "header": "Col 1"}, {"key": "col2", "header": "Col 2"}, {"key": "col3", "header": "Col 3"}]},
            ],
            "form": {
                "id": "append_form",
                "title": "Append row",
                "page": "rows",
                "trigger": "append-rows",
                "submit_label": "Append",
                "fields": [
                    {"name": "spreadsheet_id", "label": "Spreadsheet id", "type": "text", "required": True},
                    {"name": "range", "label": "Range", "type": "text", "required": True},
                    {"name": "col1", "label": "Column 1", "type": "text", "required": True},
                    {"name": "col2", "label": "Column 2", "type": "text", "required": False},
                    {"name": "col3", "label": "Column 3", "type": "text", "required": False},
                ],
            },
            "readme": _readme(
                "Google Sheets",
                "google-sheets-runtime",
                """## Connection / OAuth

Bearer tokens from Google OAuth. Scopes: `spreadsheets` and `spreadsheets.readonly`.

Staff-only. Google Sheets does not send Shopify-style HMAC webhooks; row events in the manifest are for CRM Automation configuration after HTTP writes. Durable `{entity}.updated` emission from HTTP POST is a Runtime gap — configure Automations on explicit Business Events when Runtime adds HTTP-write event emission.

## CRM Automation examples

- `row.appended` → create CRM activity
- `spreadsheet.updated` → notify staff
""",
            ),
        }
    )


def generate() -> None:
    stripe_app()
    razorpay_app()
    woocommerce_app()
    google_calendar_app()
    google_sheets_app()


if __name__ == "__main__":
    generate()

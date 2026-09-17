# Billing Pro

Create invoices, track who has paid, and follow up on unpaid bills. Optional WhatsApp reminders go through Qefro Automations after you connect WhatsApp.

Not an accounting ERP and not a payment gateway — you record payments you already received.

**Full guide:** [docs/user-guide.md](docs/user-guide.md)

## What it does

```text
CREATE INVOICE → TRACK PAYMENT → SEE WHAT IS OUTSTANDING
    → FOLLOW UP → CUSTOMER PAYS → STOP FOLLOW-UP
```

1. Create an invoice (and catalog products / line items).
2. Record payments and split them across invoices when needed.
3. See outstanding balances on the Dashboard.
4. Overdue unpaid invoices get a follow-up automatically.
5. WhatsApp reminders are configured on **Automations** (Billing Pro does not send WhatsApp itself).
6. When the invoice is paid, pending follow-ups complete.

**Example:** INV-1005 is unpaid on the due date → it becomes overdue → a follow-up is created → WhatsApp reminder (if set up) → you record the payment → paid, reminders stop.

## Install

Marketplace → **Billing Pro** → choose workspace → fill settings.

| Setting | Meaning |
| --- | --- |
| Currency | Default for invoices and payments (for example INR) |
| Invoice prefix | Start of invoice numbers (INV → INV-1001) |
| Payment terms (days) | Days from issue until due |
| Default tax rate | Default on new products and invoices |
| Follow-up interval (days) | Typical days between reminders |

Then connect **WhatsApp** under Channels, and set up follow-up automation.

## First-run checklist

- [ ] Configure business currency
- [ ] Configure invoice settings
- [ ] Add or import products
- [ ] Connect WhatsApp
- [ ] Configure follow-up automation
- [ ] Create your first invoice
- [ ] Record a payment

You're ready. Billing Pro will track outstanding payments and automatically follow up with customers.

## Daily workflow

Morning: Dashboard unpaid / overdue → work **Follow-ups** → record payments as they arrive → overdue invoices get follow-ups → Qefro sends WhatsApp if Automations is on.

## Guide

| Topic | In the guide |
| --- | --- |
| Products, tax, CSV, archive | [Products](docs/user-guide.md#products) |
| First invoice (2 × Product A ₹500 = ₹1,000), draft vs issued | [Invoices](docs/user-guide.md#invoices) |
| Fully paid / partial / why payment is separate | [Payments](docs/user-guide.md#payments) |
| Overdue → follow-up → WhatsApp → pay → stop | [Follow-ups](docs/user-guide.md#follow-ups) |
| Connect WA, Automations, Follow-up due, template, test | [WhatsApp reminders](docs/user-guide.md#whatsapp-reminders) |
| 500 unpaid invoices CSV | [Import data](docs/user-guide.md#import-data) |
| “Customer paid 5000 for INV-1005” | [Command Chat](docs/user-guide.md#command-chat) |
| Paid too early, person not saving, reminder not sending | [Troubleshooting](docs/user-guide.md#troubleshooting) |

In the app: **How this works** in the sidebar, and the Dashboard intro.

## Import sample

[docs/examples/unpaid-invoices.sample.csv](docs/examples/unpaid-invoices.sample.csv) — headers `invoice_number,name,phone,due_amount,due_date`. Map name/phone to Contacts; `due_amount` to Total.

## Command Chat

UI screens stay available. You can also say:

- Create a product called Design hours, SKU DES-01, price 2000
- Raise an invoice for 10000 due next Friday
- Customer paid 5000 UPI for INV-1005
- Follow up later — they’ll pay on Friday

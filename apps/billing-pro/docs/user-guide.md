# Billing Pro user guide

For business owners. Billing Pro helps you create invoices, track who has paid, and follow up on unpaid bills — including WhatsApp reminders if you connect WhatsApp.

This is not an accounting system and not a payment gateway. You record payments you already received (cash, UPI, bank transfer, and so on).

## Getting started

### What it does

1. You create an invoice for a customer.
2. You record payments as money comes in.
3. Billing Pro shows what is still outstanding.
4. When an invoice is overdue, a follow-up is created.
5. If WhatsApp is connected and you set up Automations, the customer gets a reminder.
6. When the invoice is fully paid, follow-ups stop.

### Install

Install **Billing Pro** from the Qefro Marketplace (Applications → Marketplace). Choose your workspace, then fill in settings.

### Settings (do these first)

| Setting | What to put | Example |
| --- | --- | --- |
| Currency | The currency you bill in | `INR` |
| Invoice prefix | Letters at the start of invoice numbers | `INV` (so invoices look like INV-1001) |
| Payment terms (days) | How many days after issue until the bill is due | `30` |
| Default tax rate | Tax you usually apply on products and invoices | `0` if you add tax yourself |
| Follow-up interval (days) | How many days you typically wait between reminders | `3` |

WhatsApp is not an install setting. Connect it under **Channels** (or Settings → Customer channels), then set up reminders on **Automations**.

### First-run checklist

After install, complete these:

- [ ] Configure business currency
- [ ] Configure invoice settings (prefix, payment terms, tax, follow-up interval)
- [ ] Add or import products
- [ ] Connect WhatsApp
- [ ] Configure follow-up automation (WhatsApp reminder)
- [ ] Create your first invoice
- [ ] Record a payment

You're ready. Billing Pro will track outstanding payments and automatically follow up with customers.

### Daily workflow

1. **Morning.** Open the Dashboard. Check **Outstanding** and **Overdue**.
2. **Follow-ups.** Open Follow-ups. Call, message, or let WhatsApp reminders go out for pending items.
3. **Record payments.** When a customer pays, open Payments (or Command Chat) and record it. Apply it to the right invoice.
4. **Overdue.** Past-due unpaid invoices become overdue and get a follow-up. You do not have to create those by hand.
5. **Reminders.** If Automations is set up, Qefro sends the WhatsApp reminder when a follow-up is due.

## Products

Products are what you sell — goods or services. Add them once, then pick them on invoices.

1. Open **Products** → **New**.
2. Enter a **name**, **SKU** (unique code), and **selling price**.
3. Optional: description, type (product or service), unit (for example kg or hour), tax rate.
4. Save.

Currency and tax default from your settings if you leave them blank.

**Edit** a product any time. To stop using it without deleting history, set **Active** to no (archive). Do not delete a product that already appears on invoices.

**CSV import:** on Products, use **Import Data**. Map columns such as name, sku / product code, price / unit price. SKU must be unique.

## Invoices

### First invoice example

You sold **2 × Product A at ₹500**.

1. Open **Invoices** → **New**.
2. Pick the **customer (contact)**. Add them under **Contacts** first if they are new.
3. Set issue date and **due date**.
4. Optional: invoice number (or let Billing Pro number it, for example INV-1001).
5. Save.
6. Open **Invoice items** → **New**. Choose the invoice, choose Product A, quantity `2`, unit price `500`.
7. Line total is **₹1,000**. The invoice total updates to ₹1,000.

If you already know the total and do not need line items yet, you can enter the total on the invoice (for example when importing old bills). When you later add items, the item totals take over.

### Draft vs issued

| Status | Meaning |
| --- | --- |
| Draft | Working copy. Not collecting yet. |
| Issued | Sent / confirmed. Waiting for payment. |
| Partially paid | Some money in, balance remaining. |
| Paid | Outstanding is zero. |
| Overdue | Due date has passed and money is still outstanding. |
| Cancelled | Voided. Not deleted. |

New invoices are **issued** unless you save them as draft.

### Invoice details

- **Items** — lines on **Invoice items**. Price is snapshotted; changing the product later does not rewrite old invoices.
- **Due date** — when you expect payment. Past this date, unpaid invoices become overdue.
- **Person / customer** — pick an existing contact. Billing Pro does not keep a second customer list.
- **Invoice number** — unique. Prefix comes from settings (INV-…).
- **Paid / outstanding** — filled in from payments you record. You do not type “paid” to mark it paid.

## Payments

A **payment** is money you received. An **allocation** is how much of that money applies to a specific invoice.

They are separate on purpose:

- One UPI of ₹5,000 might cover two invoices (₹3,000 + ₹2,000).
- One invoice might be paid in three instalments.
- Recording “paid” only on the invoice would hide that split.

### Fully paid / partial / not paid

| What happened | What you do | Invoice shows |
| --- | --- | --- |
| Customer paid the full outstanding | Record payment for that amount and allocate it to the invoice | **Paid** |
| Customer paid part | Record the amount received and allocate that amount | **Partially paid** |
| Nothing received | Do nothing | **Issued** or **Overdue** |

Use **Record payment** (Payments page or Command Chat). It asks which invoice and how much, then applies the amount.

To split one receipt across invoices, record the payment once, then use **Allocate payment** (Allocations) for each invoice.

## Follow-ups

This is the key loop: unpaid bill → follow-up → WhatsApp reminder → customer pays → stop.

### Example: INV-1005

1. You issued **INV-1005**. Due date arrives. The customer has not paid.
2. Billing Pro marks INV-1005 **overdue** and creates a **follow-up**.
3. If you connected WhatsApp and set up Automations, the customer gets a reminder.
4. They pay. You **record the payment** against INV-1005.
5. The invoice shows **paid**. Pending follow-ups for that invoice complete. Reminders stop.

You can also create a follow-up yourself: the customer said “I’ll pay Friday” → **Follow-ups** → **New** → pick the invoice → Friday.

Complete a follow-up when you have handled it (called them, they paid, or you no longer need the reminder).

## WhatsApp reminders

Billing Pro does not send WhatsApp by itself. Qefro Automations send the message using your connected WhatsApp number.

1. **Connect WhatsApp** for this workspace (Channels / Settings → Customer channels).
2. Open **Automations** in Billing Pro.
3. Create an automation. Name it something like “Invoice follow-up reminder”.
4. **When:** choose **Follow-up due** (`follow_up.due`) — the day the follow-up is due.
5. **Then:** add action **Send WhatsApp**.
6. Choose **Message** or **Template**. Example:

   Hi {{contact.name}}, invoice {{invoice.invoice_number}} still has ₹{{invoice.outstanding_amount}} due (due {{invoice.due_date}}). Please pay when you can.

   Use the fields your Automations screen offers. If a field is missing, keep the message simple: name, that a payment is due, and to reply or pay as you usually do.
7. **Test** the automation from Automations (send a test to yourself).
8. Enable it.

After the invoice is **paid**, pending follow-ups complete, so this reminder does not keep firing for that bill.

You can add a second automation on **Follow-up created** if you want a message as soon as a bill becomes overdue, not only on the follow-up date.

## Import data

Use **Import Data** on Invoices (or Products) when you have existing records. Max 2,000 rows per file.

### Example: 500 unpaid invoices

CSV headers:

```text
invoice_number,name,phone,due_amount,due_date
```

Sample rows (your file can have hundreds):

```csv
invoice_number,name,phone,due_amount,due_date
INV-1001,Riya Sharma,9876543210,15000,2026-08-01
INV-1002,Amit Patel,9123456780,8500,2026-08-15
INV-1003,Neha Gupta,9988776655,22000,2026-09-01
```

A complete sample file: [examples/unpaid-invoices.sample.csv](examples/unpaid-invoices.sample.csv).

### Mapping

| CSV column | Map to |
| --- | --- |
| invoice_number | Invoice number |
| name | Contact name (Person) |
| phone | Contact phone (Person) |
| due_amount | Total |
| due_date | Due date |

Optional extras: email, invoice date, amount paid, outstanding / balance.

**Contacts (Person):** identity uses **name / phone / email** — never a person id column. Import finds an existing contact or creates one. Pick the right mapping if the same column could mean more than one field.

Confirm the preview, then commit. Totals and overdue follow-ups update after import.

## Command Chat

You can type in Command Chat instead of filling forms. The same screens stay available.

Examples:

- “Create a product called Design hours, SKU DES-01, price 2000”
- “Raise an invoice for 10000 due next Friday”
- “Customer paid 5000 UPI for INV-1005”
- “Follow up later — they’ll pay on Friday”
- “Apply this payment to INV-1002”
- “Cancel invoice INV-1008”

If Chat asks for a missing detail (amount, date, which invoice), answer it. For a new customer, add them in **Contacts** first, then create the invoice.

## Troubleshooting

**Invoice shows paid too early.**  
A payment was allocated for the full amount. Open the invoice, then **Allocations** / **Payments**. If they only paid part, allocate only that part. Do not type status = paid by hand unless you mean to void the usual calculation.

**Customer (person) is not saving.**  
Pick an **existing contact**. Add them under **Contacts** first. Import must include name, phone, or email — not a person id.

**WhatsApp reminder is not sending.**  
Check: WhatsApp connected for this workspace? Automation **enabled**? Trigger is **Follow-up due**? Action is **Send WhatsApp**? Follow-up still **pending**? Use **Test** on the automation. Paid invoices will not keep reminding.

**Import mapping looks wrong.**  
Match headers to the table above. `due_amount` → Total (not Paid). Name/phone/email → contact identity. If SKU or invoice number already exists, uniqueness will reject or update depending on the unique field.

**Totals do not match line items.**  
Add or fix **Invoice items**. When items exist, their amounts become the invoice total. Empty invoices keep the total you typed or imported.

**I need to undo an invoice.**  
Use **Cancel invoice** (status cancelled). Related items and payments stay; the invoice is not deleted.

## Related in the app

| Page | Use it for |
| --- | --- |
| Dashboard | Outstanding, overdue, today’s payments |
| Products | Catalog |
| Invoices | Bills |
| Invoice items | Lines on a bill |
| Payments | Money received |
| Allocations | Split a payment across invoices |
| Follow-ups | Collection reminders |
| Contacts | Customers |
| Automations | WhatsApp and other reminders |
| How this works | This guide, in the app |

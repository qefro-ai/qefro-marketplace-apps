# clinic-pro-runtime

This is a metadata-only Qefro Marketplace App executed by Qefro Runtime.

- **App id:** `clinic-pro-runtime`
- **Hosting:** `runtime`
- **Architecture:** Marketplace package → metadata → Qefro Runtime → EntityService / FlowRunner / RuntimeAdapter
- **Not included:** SDK backend, custom connector, custom REST API, provider-specific Runtime branches

## What it does

Complete clinic management: patients, practitioners, slots, appointments, visits,
treatments, prescriptions, invoices, and payments — all as declarative entities
interpreted by the generic Runtime.

## Entities

| Entity | Role |
| --- | --- |
| `patient` | Patient demographics bound to Customer Hub `person_id` |
| `practitioner` | Clinician roster |
| `appointment_slot` | Bookable time windows |
| `appointment` | Scheduled appointments with status transitions |
| `visit` | In-clinic encounters |
| `treatment` | Treatments within a visit |
| `prescription` | Medication orders |
| `invoice` | Patient billing |
| `payment` | Payments against invoices |

Sensitive clinical fields (`blood_group`, `diagnosis`) exist for staff EntityService
use. Customer conversation workflows do not ask for or surface them.

## Tools (Runtime EntityService)

Staff operations use generic `entity.<name>.{create,list,get,update}` capabilities.
There is no HTTP `tools/` folder — this is not an external-system integration.

| Capability surface | Examples |
| --- | --- |
| Staff (portal UI + EntityService) | create/list/get/update patient, practitioner, slot, appointment, visit, treatment, prescription, invoice, payment |
| Customer (conversation flows) | book / list-my / cancel / reschedule appointment; list-my prescriptions; lookup-my invoice |

Customer identity comes from Customer Hub (`person_id` injected by Runtime on create).
Never trust `person_id`, `patient_id`, `email`, or `phone` supplied by the LLM/client.

## Workflows

- `book-appointment`, `reschedule-appointment`, `cancel-appointment`, `lookup-appointment`
- `create-patient`, `create-visit`, `create-prescription`
- `create-invoice`, `record-payment`

Cancel uses status update + flow `constants` (audit-preserving), not delete.

## Business Events

Declared on the manifest and via entity `status_events`:

- `patient.created` / `patient.updated`
- `appointment.created` / `.updated` / `.cancelled` / `.completed`
- `visit.created` / `.updated`
- `treatment.created` / `.completed`
- `prescription.created`
- `invoice.created` / `.paid`
- `payment.created`

## Automation examples (generic Automation host)

Configure on the Automations host page — do not embed an automation engine in the package:

| Event | Suggested actions |
| --- | --- |
| `appointment.created` | CRM activity + confirmation |
| `appointment.cancelled` | CRM activity + follow-up task |
| `visit.created` | CRM activity |
| `invoice.paid` | CRM activity + payment confirmation |

## Customer vs staff surfaces

- **Staff:** portal navigation (Patients, Appointments, Practitioners, Visits, Treatments, Prescriptions, Billing, Automations)
- **Customer:** channel conversation triggers only for own appointments / prescriptions / invoices via Hub Person identity

## Architecture

```text
clinic-pro-runtime (YAML metadata)
        ↓
Qefro Marketplace Runtime
        ↓
EntityService / FlowRunner / RuntimeAdapter
        ↓
managed storage · events · Automations host · UI host
```

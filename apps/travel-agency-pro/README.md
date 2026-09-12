# Travel Agency Pro

Metadata-only travel agency Marketplace App executed by Qefro Runtime.

No SDK, no custom server — runs entirely on Qefro's generic platform primitives.

## Entities (10)

| Entity | Description | Code Prefix |
|--------|-------------|-------------|
| destination | Travel destination locations | DST- |
| travel_package | Package offerings | PKG- |
| traveler | Travel-specific person info | TVL- |
| booking | Travel booking records | BK- |
| booking_item | Line items within a booking | BI- |
| itinerary | Travel itinerary per booking | ITN- |
| itinerary_item | Day/activity within an itinerary | ITI- |
| supplier | Service suppliers (hotel, airline, etc.) | SUP- |
| payment | Payment tracking records | PAY- |
| travel_document | Passports, visas, tickets, vouchers | DOC- |

## Workflows (14)

### Customer-facing (7)

| Workflow | Description |
|----------|-------------|
| search-packages | Search packages by destination and date |
| package-details | View package details |
| request-quote | Request a pricing quote |
| create-booking | Create a new booking |
| booking-status | Check booking status |
| modify-booking | Modify an existing booking |
| cancel-booking | Cancel a booking |

### Staff-facing (7)

| Workflow | Description |
|----------|-------------|
| create-package | Create a new travel package |
| update-package | Update package status |
| create-itinerary | Create itinerary for a booking |
| add-itinerary-item | Add activity to itinerary |
| confirm-booking | Confirm a pending booking |
| record-payment | Record payment for a booking |
| assign-supplier | Assign supplier to booking item |

## Events (25)

destination.created, destination.updated, travel_package.created, travel_package.updated, travel_package.status_changed, traveler.created, traveler.updated, booking.created, booking.updated, booking.confirmed, booking.cancelled, booking.completed, booking_item.created, booking_item.updated, itinerary.created, itinerary.updated, itinerary_item.created, itinerary_item.updated, supplier.created, supplier.updated, payment.created, payment.updated, payment.status_changed, travel_document.created, travel_document.updated

## UI Screens (12)

Dashboard, Packages, Destinations, Bookings, Travelers, Itineraries, Suppliers, Payments, Documents, Contacts, Automations, Roles

## Customer Journey

```
Customer → WhatsApp → Search packages → Select package → Provide traveler info
→ Booking created (pending) → Staff confirms → Payment recorded → Itinerary sent
```

## Architecture

This app is 100% metadata-driven. No travel-specific code exists in the platform.
All functionality uses generic Qefro primitives: EntityService, FlowRunner, CRM Automation, and Customer Hub Person identity.

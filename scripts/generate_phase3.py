"""Phase 3 native Qefro vertical Marketplace Apps (entity.* only)."""

from __future__ import annotations

from gen_lib import enum_field, field, person_field, slot, trigger, write_vertical_app


def _readme(title: str, app_id: str, events: str, automations: str) -> str:
    return f"""# {app_id}

Native Qefro Marketplace App for {title}.

- **App id:** `{app_id}`
- **Hosting:** `runtime`
- **Execution:** `entity.*` via FlowRunner → RuntimeAdapter (managed storage)

This is not a wrapper around an external API. Contacts stay on the platform
Person model (`person_id`). CRM Automations are configured on the Automations
host page and consume Business Events — they are not executed inline from tools.

## Business Events

{events}

## CRM Automation examples

{automations}

`entity.create` emits `{{entity}}.created`. `entity.update` currently does not
emit `{{entity}}.updated` in Runtime; declare the event so Automations can bind
when that generic capability exists. Cancel flows use update of `status` rather
than delete so records remain auditable.
"""


def _ask(name: str, message: str) -> dict[str, str]:
    return {"field": name, "message": message}


def appointment_app() -> None:
    write_vertical_app(
        {
            "id": "appointment-runtime",
            "name": "Appointments",
            "description": "Services, staff, availability, and bookings as a native Qefro business application",
            "category": "scheduling",
            "tags": ["appointments", "booking", "runtime"],
            "comments": [
                "Appointment / Booking — native metadata Marketplace App.",
                "Same installer, FlowRunner, and EntityService as Restaurant Pro. No SDK process.",
            ],
            "entities": [
                {
                    "id": "service",
                    "name": "Service",
                    "description": "Bookable service",
                    "prefix": "SVC-",
                    "fields": [field("name", "string", True), field("duration_minutes", "integer", True), field("price", "float"), enum_field("status", ["active", "inactive"])],
                },
                {
                    "id": "staff_member",
                    "name": "Staff member",
                    "description": "Person who delivers a service",
                    "fields": [field("name", "string", True), field("role", "string"), person_field("Staff Person identity when the teammate is also a Qefro user")],
                },
                {
                    "id": "availability_slot",
                    "name": "Availability slot",
                    "description": "Open window for bookings",
                    "fields": [field("staff_name", "string", True), field("date", "date", True), field("start_time", "string"), field("end_time", "string"), enum_field("status", ["open", "held", "booked"])],
                },
                {
                    "id": "appointment",
                    "name": "Appointment",
                    "description": "Customer booking bound to Person",
                    "prefix": "A-",
                    "fields": [
                        field("guest_name", "string", True),
                        field("service_name", "string", True),
                        field("staff_name", "string"),
                        field("date", "date", True),
                        field("time", "string"),
                        enum_field("status", ["scheduled", "confirmed", "completed", "cancelled", "no_show"]),
                        person_field("Existing Qefro Person identity (never an app-local CRM)"),
                    ],
                },
            ],
            "flows": [
                {
                    "id": "create-appointment",
                    "name": "Create appointment",
                    "description": "Book an appointment through Qefro Runtime",
                    "tool": "entity.appointment.create",
                    "asks": [_ask("service_name", "Which service should we book?"), _ask("date", "Which date?"), _ask("guest_name", "What name should the appointment be under?")],
                    "input_map": {"guest_name": "guest_name", "service_name": "service_name", "date": "date", "time": "time", "staff_name": "staff_name"},
                    "confirm": "Appointment booked for {{guest_name}} on {{date}}.",
                },
                {
                    "id": "reschedule-appointment",
                    "name": "Reschedule appointment",
                    "description": "Update appointment date/time through Qefro Runtime",
                    "tool": "entity.appointment.update",
                    "asks": [_ask("id", "Which appointment id should we move?"), _ask("date", "New date?"), _ask("time", "New time?")],
                    "input_map": {"id": "id", "date": "date", "time": "time"},
                    "confirm": "Appointment {{id}} rescheduled to {{date}}.",
                },
                {
                    "id": "cancel-appointment",
                    "name": "Cancel appointment",
                    "description": "Mark an appointment cancelled through Qefro Runtime",
                    "tool": "entity.appointment.update",
                    "asks": [_ask("id", "Which appointment id should we cancel?"), _ask("status", "Type cancelled to confirm.")],
                    "input_map": {"id": "id", "status": "status"},
                    "confirm": "Appointment {{id}} cancelled.",
                },
                {
                    "id": "lookup-appointment",
                    "name": "Lookup appointment",
                    "description": "Fetch one appointment by id",
                    "tool": "entity.appointment.get",
                    "asks": [_ask("id", "Which appointment id?")],
                    "input_map": {"id": "id"},
                    "confirm": "Here is appointment {{id}}.",
                },
            ],
            "events": ["appointment.created", "appointment.updated", "appointment.cancelled", "booking.created"],
            "triggers": [
                trigger("book_appointment", "create-appointment", "appointment_input", ["book an appointment", "schedule an appointment", "make a booking"], ["appointment", "booked"], ["service_name", "date"], "Appointment booked for {{guest_name}} on {{date}}."),
                trigger("reschedule_appointment", "reschedule-appointment", "reschedule_input", ["reschedule my appointment", "move my booking"], ["rescheduled"], ["id", "date"], "Appointment {{id}} rescheduled to {{date}}."),
                trigger("cancel_appointment", "cancel-appointment", "cancel_input", ["cancel my appointment", "cancel the booking"], ["cancelled"], ["id"], "Appointment {{id}} cancelled."),
                trigger("lookup_appointment", "lookup-appointment", "lookup_input", ["find my appointment", "appointment status"], ["appointment"], ["id"], "Here is appointment {{id}}."),
            ],
            "slots": [
                slot("guest_name", ["guest", "name", "customer"], "person_name", identity="person_name"),
                slot("service_name", ["service", "treatment", "session type"], "string"),
                slot("staff_name", ["staff", "with", "practitioner"], "string"),
                slot("date", ["date", "tomorrow"], "date"),
                slot("time", ["time"], "time", chip_prefix="time"),
                slot("id", ["appointment", "booking id"], "string"),
                slot("status", ["status", "cancelled"], "string"),
            ],
            "intro": "Native Qefro business app. Chat “book an appointment tomorrow” starts create-appointment on the shared FlowRunner. Records persist in managed storage. Contacts stay on Person CRM. Automations bind to appointment.created.",
            "theme": {"primary": "#0f766e", "secondary": "#134e4a", "accent": "#14b8a6", "background": "#f0fdfa", "surface": "#ffffff", "text": "#134e4a"},
            "sources": [("appointments", "appointment"), ("services", "service"), ("staff", "staff_member"), ("slots", "availability_slot")],
            "tables": [
                {"id": "appointments_table", "title": "Appointments", "source": "appointments", "icon": "calendar", "columns": [{"key": "guest_name", "header": "Guest"}, {"key": "service_name", "header": "Service"}, {"key": "date", "header": "Date"}, {"key": "status", "header": "Status"}]},
                {"id": "services_table", "title": "Services", "source": "services", "icon": "list", "columns": [{"key": "name", "header": "Name"}, {"key": "duration_minutes", "header": "Minutes"}, {"key": "price", "header": "Price"}]},
                {"id": "staff_table", "title": "Staff", "source": "staff", "icon": "users", "columns": [{"key": "name", "header": "Name"}, {"key": "role", "header": "Role"}]},
                {"id": "slots_table", "title": "Availability", "source": "slots", "icon": "clock", "columns": [{"key": "staff_name", "header": "Staff"}, {"key": "date", "header": "Date"}, {"key": "status", "header": "Status"}]},
            ],
            "form": {
                "id": "appointment_form",
                "title": "New appointment",
                "page": "appointments",
                "trigger": "create-appointment",
                "submit_label": "Book",
                "fields": [
                    {"name": "guest_name", "label": "Guest name", "type": "text", "required": True},
                    {"name": "service_name", "label": "Service", "type": "text", "required": True},
                    {"name": "date", "label": "Date", "type": "date", "required": True},
                    {"name": "time", "label": "Time", "type": "time", "required": False},
                ],
            },
            "status": {"id": "appointments_status", "title": "Appointments", "source": "appointments", "label_field": "guest_name"},
            "readme": _readme(
                "appointments and bookings",
                "appointment-runtime",
                "- `appointment.created` / `booking.created`\n- `appointment.updated`\n- `appointment.cancelled`",
                "- Booking created → send confirmation, schedule reminder\n- Appointment cancelled → create follow-up task",
            ),
        }
    )


def field_service_app() -> None:
    write_vertical_app(
        {
            "id": "field-service-runtime",
            "name": "Field Service",
            "description": "Sites, technicians, parts, and work orders as a native Qefro business application",
            "category": "operations",
            "tags": ["field-service", "work-orders", "runtime"],
            "comments": ["Field Service — native metadata Marketplace App. No external FSM vendor wrapper."],
            "entities": [
                {"id": "site", "name": "Site", "description": "Customer site or location", "prefix": "SITE-", "fields": [field("name", "string", True), field("address", "string", True), field("contact_name", "string")]},
                {"id": "technician", "name": "Technician", "description": "Field technician", "fields": [field("name", "string", True), field("skill", "string"), person_field("Existing Qefro Person identity")]},
                {"id": "part", "name": "Part", "description": "Spare part used on jobs", "fields": [field("sku", "string", True), field("name", "string", True), field("quantity_on_hand", "integer")]},
                {
                    "id": "work_order",
                    "name": "Work order",
                    "description": "Job at a site bound to Person",
                    "prefix": "WO-",
                    "fields": [
                        field("site_name", "string", True),
                        field("summary", "string", True),
                        field("technician_name", "string"),
                        field("scheduled_date", "date"),
                        enum_field("status", ["open", "assigned", "in_progress", "completed", "cancelled"]),
                        person_field("Existing Qefro Person identity"),
                    ],
                },
            ],
            "flows": [
                {
                    "id": "create-work-order",
                    "name": "Create work order",
                    "description": "Open a field job through Qefro Runtime",
                    "tool": "entity.work_order.create",
                    "asks": [_ask("site_name", "Which site?"), _ask("summary", "What needs to be done?"), _ask("scheduled_date", "Which date?")],
                    "input_map": {"site_name": "site_name", "summary": "summary", "scheduled_date": "scheduled_date", "technician_name": "technician_name"},
                    "confirm": "Work order created for {{site_name}}.",
                },
                {
                    "id": "update-work-order",
                    "name": "Update work order",
                    "description": "Assign or edit a work order",
                    "tool": "entity.work_order.update",
                    "asks": [_ask("id", "Which work order id?"), _ask("technician_name", "Assign which technician?"), _ask("status", "New status?")],
                    "input_map": {"id": "id", "technician_name": "technician_name", "status": "status"},
                    "confirm": "Work order {{id}} updated.",
                },
                {
                    "id": "complete-work-order",
                    "name": "Complete work order",
                    "description": "Mark a job completed",
                    "tool": "entity.work_order.update",
                    "asks": [_ask("id", "Which work order id is done?"), _ask("status", "Type completed to confirm.")],
                    "input_map": {"id": "id", "status": "status"},
                    "confirm": "Work order {{id}} completed.",
                },
                {
                    "id": "lookup-work-order",
                    "name": "Lookup work order",
                    "description": "Fetch one work order",
                    "tool": "entity.work_order.get",
                    "asks": [_ask("id", "Which work order id?")],
                    "input_map": {"id": "id"},
                    "confirm": "Here is work order {{id}}.",
                },
            ],
            "events": ["work_order.created", "work_order.updated", "work_order.completed", "work_order.cancelled"],
            "triggers": [
                trigger("create_work_order", "create-work-order", "wo_input", ["create a work order", "open a job", "dispatch a technician"], ["work order"], ["site_name", "summary"], "Work order created for {{site_name}}."),
                trigger("update_work_order", "update-work-order", "wo_update", ["assign the work order", "update the job"], ["updated"], ["id"], "Work order {{id}} updated."),
                trigger("complete_work_order", "complete-work-order", "wo_complete", ["complete the work order", "close the job"], ["completed"], ["id"], "Work order {{id}} completed."),
                trigger("lookup_work_order", "lookup-work-order", "wo_lookup", ["find the work order", "job status"], ["work order"], ["id"], "Here is work order {{id}}."),
            ],
            "slots": [
                slot("site_name", ["site", "location", "address"], "string"),
                slot("summary", ["job", "issue", "summary"], "string"),
                slot("technician_name", ["technician", "engineer"], "string"),
                slot("scheduled_date", ["date", "tomorrow"], "date"),
                slot("status", ["status"], "string"),
                slot("id", ["work order", "job id"], "string"),
            ],
            "intro": "Native field service app. Chat “create a work order” persists in managed storage. Automations bind to work_order.created — notify staff, create CRM activity.",
            "theme": {"primary": "#b45309", "secondary": "#1c1917", "accent": "#f59e0b", "background": "#fffbeb", "surface": "#ffffff", "text": "#1c1917"},
            "sources": [("work_orders", "work_order"), ("sites", "site"), ("technicians", "technician"), ("parts", "part")],
            "tables": [
                {"id": "wo_table", "title": "Work orders", "source": "work_orders", "icon": "clipboard", "columns": [{"key": "site_name", "header": "Site"}, {"key": "summary", "header": "Summary"}, {"key": "status", "header": "Status"}]},
                {"id": "sites_table", "title": "Sites", "source": "sites", "icon": "map", "columns": [{"key": "name", "header": "Name"}, {"key": "address", "header": "Address"}]},
                {"id": "tech_table", "title": "Technicians", "source": "technicians", "icon": "users", "columns": [{"key": "name", "header": "Name"}, {"key": "skill", "header": "Skill"}]},
                {"id": "parts_table", "title": "Parts", "source": "parts", "icon": "package", "columns": [{"key": "sku", "header": "SKU"}, {"key": "quantity_on_hand", "header": "Qty"}]},
            ],
            "form": {
                "id": "wo_form",
                "title": "New work order",
                "page": "work_orders",
                "trigger": "create-work-order",
                "submit_label": "Create",
                "fields": [
                    {"name": "site_name", "label": "Site", "type": "text", "required": True},
                    {"name": "summary", "label": "Summary", "type": "text", "required": True},
                    {"name": "scheduled_date", "label": "Date", "type": "date", "required": False},
                ],
            },
            "status": {"id": "wo_status", "title": "Work orders", "source": "work_orders", "label_field": "summary"},
            "readme": _readme("field service", "field-service-runtime", "- `work_order.created` / `.updated` / `.completed` / `.cancelled`", "- New work order → notify staff, create CRM activity\n- Completed job → send customer confirmation"),
        }
    )


def education_app() -> None:
    write_vertical_app(
        {
            "id": "education-runtime",
            "name": "Education",
            "description": "Courses, enrollments, sessions, and assignments as a native Qefro coaching application",
            "category": "education",
            "tags": ["education", "coaching", "runtime"],
            "comments": ["Education / Coaching — native metadata Marketplace App."],
            "entities": [
                {"id": "course", "name": "Course", "description": "Program or cohort", "prefix": "CRS-", "fields": [field("title", "string", True), field("level", "string"), enum_field("status", ["draft", "open", "closed"])]},
                {
                    "id": "enrollment",
                    "name": "Enrollment",
                    "description": "Learner enrollment bound to Person",
                    "prefix": "ENR-",
                    "fields": [
                        field("learner_name", "string", True),
                        field("course_title", "string", True),
                        field("date", "date"),
                        enum_field("status", ["applied", "active", "completed", "withdrawn"]),
                        person_field("Existing Qefro Person identity"),
                    ],
                },
                {"id": "session", "name": "Session", "description": "Class or coaching session", "prefix": "SES-", "fields": [field("course_title", "string", True), field("date", "date", True), field("time", "string"), enum_field("status", ["scheduled", "completed", "cancelled"])]},
                {"id": "assignment", "name": "Assignment", "description": "Learner assignment", "fields": [field("title", "string", True), field("course_title", "string"), enum_field("status", ["assigned", "submitted", "reviewed"])]},
            ],
            "flows": [
                {
                    "id": "enroll-student",
                    "name": "Enroll student",
                    "description": "Create an enrollment through Qefro Runtime",
                    "tool": "entity.enrollment.create",
                    "asks": [_ask("learner_name", "Learner name?"), _ask("course_title", "Which course?")],
                    "input_map": {"learner_name": "learner_name", "course_title": "course_title", "date": "date"},
                    "confirm": "{{learner_name}} enrolled in {{course_title}}.",
                },
                {
                    "id": "schedule-session",
                    "name": "Schedule session",
                    "description": "Create a class session",
                    "tool": "entity.session.create",
                    "asks": [_ask("course_title", "Which course?"), _ask("date", "Which date?"), _ask("time", "What time?")],
                    "input_map": {"course_title": "course_title", "date": "date", "time": "time"},
                    "confirm": "Session scheduled for {{course_title}} on {{date}}.",
                },
                {
                    "id": "complete-session",
                    "name": "Complete session",
                    "description": "Mark a session completed",
                    "tool": "entity.session.update",
                    "asks": [_ask("id", "Which session id?"), _ask("status", "Type completed to confirm.")],
                    "input_map": {"id": "id", "status": "status"},
                    "confirm": "Session {{id}} completed.",
                },
                {
                    "id": "lookup-enrollment",
                    "name": "Lookup enrollment",
                    "description": "Fetch one enrollment",
                    "tool": "entity.enrollment.get",
                    "asks": [_ask("id", "Which enrollment id?")],
                    "input_map": {"id": "id"},
                    "confirm": "Here is enrollment {{id}}.",
                },
            ],
            "events": ["enrollment.created", "session.created", "session.completed", "assignment.created"],
            "triggers": [
                trigger("enroll_student", "enroll-student", "enroll_input", ["enroll a student", "sign up for the course"], ["enrolled"], ["learner_name", "course_title"], "{{learner_name}} enrolled in {{course_title}}."),
                trigger("schedule_session", "schedule-session", "session_input", ["schedule a class", "book a coaching session"], ["scheduled"], ["course_title", "date"], "Session scheduled for {{course_title}} on {{date}}."),
                trigger("complete_session", "complete-session", "session_complete", ["complete the session", "mark class done"], ["completed"], ["id"], "Session {{id}} completed."),
                trigger("lookup_enrollment", "lookup-enrollment", "enroll_lookup", ["find the enrollment", "enrollment status"], ["enrollment"], ["id"], "Here is enrollment {{id}}."),
            ],
            "slots": [
                slot("learner_name", ["learner", "student", "name"], "person_name", identity="person_name"),
                slot("course_title", ["course", "program", "class"], "string"),
                slot("date", ["date", "tomorrow"], "date"),
                slot("time", ["time"], "time", chip_prefix="time"),
                slot("id", ["enrollment", "session id"], "string"),
                slot("status", ["status", "completed"], "string"),
            ],
            "intro": "Native education/coaching app. Chat “enroll a student” or “schedule a class” uses EntityService. Automations: enrollment.created → send confirmation.",
            "theme": {"primary": "#1d4ed8", "secondary": "#1e3a8a", "accent": "#60a5fa", "background": "#eff6ff", "surface": "#ffffff", "text": "#1e3a8a"},
            "sources": [("enrollments", "enrollment"), ("courses", "course"), ("sessions", "session"), ("assignments", "assignment")],
            "tables": [
                {"id": "enroll_table", "title": "Enrollments", "source": "enrollments", "icon": "users", "columns": [{"key": "learner_name", "header": "Learner"}, {"key": "course_title", "header": "Course"}, {"key": "status", "header": "Status"}]},
                {"id": "courses_table", "title": "Courses", "source": "courses", "icon": "list", "columns": [{"key": "title", "header": "Title"}, {"key": "status", "header": "Status"}]},
                {"id": "sessions_table", "title": "Sessions", "source": "sessions", "icon": "calendar", "columns": [{"key": "course_title", "header": "Course"}, {"key": "date", "header": "Date"}, {"key": "status", "header": "Status"}]},
                {"id": "assignments_table", "title": "Assignments", "source": "assignments", "icon": "clipboard", "columns": [{"key": "title", "header": "Title"}, {"key": "status", "header": "Status"}]},
            ],
            "form": {
                "id": "enroll_form",
                "title": "Enroll learner",
                "page": "enrollments",
                "trigger": "enroll-student",
                "submit_label": "Enroll",
                "fields": [
                    {"name": "learner_name", "label": "Learner", "type": "text", "required": True},
                    {"name": "course_title", "label": "Course", "type": "text", "required": True},
                    {"name": "date", "label": "Date", "type": "date", "required": False},
                ],
            },
            "status": {"id": "enroll_status", "title": "Enrollments", "source": "enrollments", "label_field": "learner_name"},
            "readme": _readme("education and coaching", "education-runtime", "- `enrollment.created`\n- `session.created` / `session.completed`\n- `assignment.created`", "- Enrollment created → send confirmation\n- Session scheduled → reminder"),
        }
    )


def clinic_app() -> None:
    write_vertical_app(
        {
            "id": "clinic-runtime",
            "name": "Clinic",
            "description": "Practitioners, slots, visits, and treatments as a native Qefro clinic application",
            "category": "healthcare",
            "tags": ["clinic", "healthcare", "runtime"],
            "comments": [
                "Healthcare / Clinic — native operational metadata app, not an EHR or payer integration.",
                "Stores visit logistics (who/when/reason/status), not clinical charts.",
            ],
            "entities": [
                {"id": "practitioner", "name": "Practitioner", "description": "Clinician or coach", "fields": [field("name", "string", True), field("specialty", "string"), person_field("Existing Qefro Person identity")]},
                {"id": "appointment_slot", "name": "Appointment slot", "description": "Open clinic slot", "fields": [field("practitioner_name", "string", True), field("date", "date", True), field("time", "string"), enum_field("status", ["open", "held", "booked"])]},
                {
                    "id": "visit",
                    "name": "Visit",
                    "description": "Clinic visit bound to Person",
                    "prefix": "V-",
                    "fields": [
                        field("patient_name", "string", True),
                        field("practitioner_name", "string"),
                        field("reason", "string"),
                        field("date", "date", True),
                        field("time", "string"),
                        enum_field("status", ["scheduled", "checked_in", "completed", "cancelled", "no_show"]),
                        person_field("Existing Qefro Person identity"),
                    ],
                },
                {"id": "treatment", "name": "Treatment", "description": "Treatment plan item (operational, not a clinical record)", "fields": [field("name", "string", True), field("visit_id", "string"), enum_field("status", ["planned", "in_progress", "done"])]},
            ],
            "flows": [
                {
                    "id": "book-visit",
                    "name": "Book visit",
                    "description": "Schedule a clinic visit through Qefro Runtime",
                    "tool": "entity.visit.create",
                    "asks": [_ask("patient_name", "Patient name?"), _ask("date", "Which date?"), _ask("reason", "Reason for visit?")],
                    "input_map": {"patient_name": "patient_name", "date": "date", "time": "time", "reason": "reason", "practitioner_name": "practitioner_name"},
                    "confirm": "Visit booked for {{patient_name}} on {{date}}.",
                },
                {
                    "id": "reschedule-visit",
                    "name": "Reschedule visit",
                    "description": "Move a clinic visit",
                    "tool": "entity.visit.update",
                    "asks": [_ask("id", "Which visit id?"), _ask("date", "New date?"), _ask("time", "New time?")],
                    "input_map": {"id": "id", "date": "date", "time": "time"},
                    "confirm": "Visit {{id}} rescheduled to {{date}}.",
                },
                {
                    "id": "cancel-visit",
                    "name": "Cancel visit",
                    "description": "Cancel a clinic visit",
                    "tool": "entity.visit.update",
                    "asks": [_ask("id", "Which visit id should we cancel?"), _ask("status", "Type cancelled to confirm.")],
                    "input_map": {"id": "id", "status": "status"},
                    "confirm": "Visit {{id}} cancelled.",
                },
                {
                    "id": "lookup-visit",
                    "name": "Lookup visit",
                    "description": "Fetch one visit",
                    "tool": "entity.visit.get",
                    "asks": [_ask("id", "Which visit id?")],
                    "input_map": {"id": "id"},
                    "confirm": "Here is visit {{id}}.",
                },
            ],
            "events": ["visit.created", "visit.updated", "visit.cancelled", "treatment.created"],
            "triggers": [
                trigger("book_visit", "book-visit", "visit_input", ["book a visit", "schedule an appointment at the clinic"], ["visit", "booked"], ["patient_name", "date"], "Visit booked for {{patient_name}} on {{date}}."),
                trigger("reschedule_visit", "reschedule-visit", "visit_reschedule", ["reschedule the visit", "move my clinic appointment"], ["rescheduled"], ["id", "date"], "Visit {{id}} rescheduled to {{date}}."),
                trigger("cancel_visit", "cancel-visit", "visit_cancel", ["cancel the visit", "cancel clinic appointment"], ["cancelled"], ["id"], "Visit {{id}} cancelled."),
                trigger("lookup_visit", "lookup-visit", "visit_lookup", ["find my visit", "visit status"], ["visit"], ["id"], "Here is visit {{id}}."),
            ],
            "slots": [
                slot("patient_name", ["patient", "name"], "person_name", identity="person_name"),
                slot("practitioner_name", ["doctor", "practitioner", "clinician"], "string"),
                slot("reason", ["reason", "complaint"], "string"),
                slot("date", ["date", "tomorrow"], "date"),
                slot("time", ["time"], "time", chip_prefix="time"),
                slot("id", ["visit", "appointment id"], "string"),
                slot("status", ["status", "cancelled"], "string"),
            ],
            "intro": "Native clinic operations app — visits and slots, not an EHR. Chat “book a visit tomorrow” uses EntityService. Automations: visit.created → send confirmation.",
            "theme": {"primary": "#0e7490", "secondary": "#164e63", "accent": "#22d3ee", "background": "#ecfeff", "surface": "#ffffff", "text": "#164e63"},
            "sources": [("visits", "visit"), ("practitioners", "practitioner"), ("slots", "appointment_slot"), ("treatments", "treatment")],
            "tables": [
                {"id": "visits_table", "title": "Visits", "source": "visits", "icon": "stethoscope", "columns": [{"key": "patient_name", "header": "Patient"}, {"key": "date", "header": "Date"}, {"key": "status", "header": "Status"}]},
                {"id": "practitioners_table", "title": "Practitioners", "source": "practitioners", "icon": "users", "columns": [{"key": "name", "header": "Name"}, {"key": "specialty", "header": "Specialty"}]},
                {"id": "slots_table", "title": "Slots", "source": "slots", "icon": "calendar", "columns": [{"key": "practitioner_name", "header": "Practitioner"}, {"key": "date", "header": "Date"}, {"key": "status", "header": "Status"}]},
                {"id": "treatments_table", "title": "Treatments", "source": "treatments", "icon": "clipboard", "columns": [{"key": "name", "header": "Name"}, {"key": "status", "header": "Status"}]},
            ],
            "form": {
                "id": "visit_form",
                "title": "Book visit",
                "page": "visits",
                "trigger": "book-visit",
                "submit_label": "Book",
                "fields": [
                    {"name": "patient_name", "label": "Patient name", "type": "text", "required": True},
                    {"name": "reason", "label": "Reason", "type": "text", "required": False},
                    {"name": "date", "label": "Date", "type": "date", "required": True},
                    {"name": "time", "label": "Time", "type": "time", "required": False},
                ],
            },
            "status": {"id": "visits_status", "title": "Visits", "source": "visits", "label_field": "patient_name"},
            "readme": _readme("clinic operations", "clinic-runtime", "- `visit.created` / `.updated` / `.cancelled`\n- `treatment.created`", "- Visit created → send confirmation, schedule reminder\n- Visit cancelled → follow-up task"),
        }
    )


def logistics_app() -> None:
    write_vertical_app(
        {
            "id": "logistics-runtime",
            "name": "Logistics",
            "description": "Vehicles, consignments, shipments, and stops as a native Qefro logistics application",
            "category": "logistics",
            "tags": ["logistics", "shipping", "runtime"],
            "comments": ["Logistics — native metadata Marketplace App. Not a carrier API wrapper."],
            "entities": [
                {"id": "vehicle", "name": "Vehicle", "description": "Fleet vehicle", "prefix": "VEH-", "fields": [field("label", "string", True), field("capacity", "integer"), enum_field("status", ["available", "in_use", "maintenance"])]},
                {
                    "id": "consignment",
                    "name": "Consignment",
                    "description": "Goods consignment bound to Person",
                    "prefix": "CON-",
                    "fields": [
                        field("reference", "string", True),
                        field("customer_name", "string", True),
                        field("weight", "float"),
                        person_field("Existing Qefro Person identity"),
                    ],
                },
                {
                    "id": "shipment",
                    "name": "Shipment",
                    "description": "Shipment movement",
                    "prefix": "SHP-",
                    "fields": [
                        field("origin", "string", True),
                        field("destination", "string", True),
                        field("vehicle_label", "string"),
                        field("scheduled_date", "date"),
                        enum_field("status", ["draft", "in_transit", "delivered", "cancelled", "exception"]),
                        person_field("Existing Qefro Person identity"),
                    ],
                },
                {"id": "stop", "name": "Stop", "description": "Stop on a shipment", "fields": [field("shipment_id", "string", True), field("address", "string", True), field("sequence", "integer"), enum_field("status", ["pending", "arrived", "completed", "skipped"])]},
            ],
            "flows": [
                {
                    "id": "create-shipment",
                    "name": "Create shipment",
                    "description": "Create a shipment through Qefro Runtime",
                    "tool": "entity.shipment.create",
                    "asks": [_ask("origin", "Origin?"), _ask("destination", "Destination?"), _ask("scheduled_date", "Ship date?")],
                    "input_map": {"origin": "origin", "destination": "destination", "scheduled_date": "scheduled_date", "vehicle_label": "vehicle_label"},
                    "confirm": "Shipment created from {{origin}} to {{destination}}.",
                },
                {
                    "id": "update-shipment-status",
                    "name": "Update shipment status",
                    "description": "Advance shipment state",
                    "tool": "entity.shipment.update",
                    "asks": [_ask("id", "Which shipment id?"), _ask("status", "New status (in_transit, delivered, exception)?")],
                    "input_map": {"id": "id", "status": "status"},
                    "confirm": "Shipment {{id}} is now {{status}}.",
                },
                {
                    "id": "cancel-shipment",
                    "name": "Cancel shipment",
                    "description": "Cancel a shipment",
                    "tool": "entity.shipment.update",
                    "asks": [_ask("id", "Which shipment id should we cancel?"), _ask("status", "Type cancelled to confirm.")],
                    "input_map": {"id": "id", "status": "status"},
                    "confirm": "Shipment {{id}} cancelled.",
                },
                {
                    "id": "lookup-shipment",
                    "name": "Lookup shipment",
                    "description": "Fetch one shipment",
                    "tool": "entity.shipment.get",
                    "asks": [_ask("id", "Which shipment id?")],
                    "input_map": {"id": "id"},
                    "confirm": "Here is shipment {{id}}.",
                },
            ],
            "events": ["shipment.created", "shipment.updated", "shipment.cancelled", "consignment.created"],
            "triggers": [
                trigger("create_shipment", "create-shipment", "shipment_input", ["create a shipment", "book a delivery"], ["shipment"], ["origin", "destination"], "Shipment created from {{origin}} to {{destination}}."),
                trigger("update_shipment_status", "update-shipment-status", "shipment_status", ["update shipment status", "mark delivered"], ["updated"], ["id", "status"], "Shipment {{id}} is now {{status}}."),
                trigger("cancel_shipment", "cancel-shipment", "shipment_cancel", ["cancel the shipment", "stop the delivery"], ["cancelled"], ["id"], "Shipment {{id}} cancelled."),
                trigger("lookup_shipment", "lookup-shipment", "shipment_lookup", ["track shipment", "where is my shipment"], ["shipment"], ["id"], "Here is shipment {{id}}."),
            ],
            "slots": [
                slot("origin", ["origin", "from", "pickup"], "string"),
                slot("destination", ["destination", "to", "drop"], "string"),
                slot("vehicle_label", ["vehicle", "truck"], "string"),
                slot("scheduled_date", ["date", "tomorrow"], "date"),
                slot("status", ["status", "delivered", "in transit"], "string"),
                slot("id", ["shipment", "tracking"], "string"),
            ],
            "intro": "Native logistics app. Chat “create a shipment” or “mark delivered” uses EntityService. Automations: shipment.cancelled → customer follow-up task.",
            "theme": {"primary": "#1e3a8a", "secondary": "#0f172a", "accent": "#38bdf8", "background": "#f8fafc", "surface": "#ffffff", "text": "#0f172a"},
            "sources": [("shipments", "shipment"), ("consignments", "consignment"), ("vehicles", "vehicle"), ("stops", "stop")],
            "tables": [
                {"id": "shipments_table", "title": "Shipments", "source": "shipments", "icon": "map", "columns": [{"key": "origin", "header": "Origin"}, {"key": "destination", "header": "Destination"}, {"key": "status", "header": "Status"}]},
                {"id": "consignments_table", "title": "Consignments", "source": "consignments", "icon": "package", "columns": [{"key": "reference", "header": "Ref"}, {"key": "customer_name", "header": "Customer"}]},
                {"id": "vehicles_table", "title": "Vehicles", "source": "vehicles", "icon": "clipboard", "columns": [{"key": "label", "header": "Label"}, {"key": "status", "header": "Status"}]},
                {"id": "stops_table", "title": "Stops", "source": "stops", "icon": "list", "columns": [{"key": "address", "header": "Address"}, {"key": "status", "header": "Status"}]},
            ],
            "form": {
                "id": "shipment_form",
                "title": "New shipment",
                "page": "shipments",
                "trigger": "create-shipment",
                "submit_label": "Create",
                "fields": [
                    {"name": "origin", "label": "Origin", "type": "text", "required": True},
                    {"name": "destination", "label": "Destination", "type": "text", "required": True},
                    {"name": "scheduled_date", "label": "Date", "type": "date", "required": False},
                ],
            },
            "status": {"id": "shipments_status", "title": "Shipments", "source": "shipments", "label_field": "destination"},
            "readme": _readme("logistics", "logistics-runtime", "- `shipment.created` / `.updated` / `.cancelled`\n- `consignment.created`", "- Order/shipment cancelled → customer follow-up task\n- Shipment created → send confirmation"),
        }
    )


def generate() -> None:
    appointment_app()
    field_service_app()
    education_app()
    clinic_app()
    logistics_app()


if __name__ == "__main__":
    generate()

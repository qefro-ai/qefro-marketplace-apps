# Workflows and events

Eight `create-*` workflows correspond to the eight entities. Each is staff-only, asks required fields, resolves required related records using `entity.<target>.list`, uses `output` plus string `choices_from`, writes through `entity.<name>.create` with `execution: runtime`, then completes. Empty relation lists have explicit messages. These workflows use the Real Estate Pro pattern and compile through the production `FlowDefinition::compile_business_flow`.

Generic entity forms additionally provide direct create/edit/detail/archive with runtime authorization. Updates use host-supplied current record versions; no workflow lets an LLM invent version or tenant authority. Status defaults create employees as planned and contracts as draft. Administrative review/activation is a native edit.

Renewal: create a new contract linked to `previous_contract`, review its dates and overlap, then update prior status to renewed. This is deliberately not claimed atomic. Termination: record last working/cancellation dates and reason, update contract status, then review employee status. Site assignment and transfer use the employee's Assigned Site field. Production storage closes open active periods and creates the new period in the same transaction when that field changes. The history uses the destination site's business date, with Asia/Dubai as the fallback. Earlier periods require their actual dates to be entered manually.

`contract.expiry_due` and `identity.expiry_due` use existing guarded date watches. `employee.terminated`, `contract.terminated`, `contract.renewed`, `contract.completed` are status events. The app emits business facts; authorized tenant administrators configure existing CRM automation actions. Offset reminders, daily/weekly summaries, notification delivery and automatic status completion are not implemented. No default recipient, webhook URL, credential or live channel is embedded.

Flow execution tests must additionally exercise submitted variables, exact relation resolution, authorization and persistence in the running services. Compilation is not execution; browser mocked writes are not FlowRunner execution.

Four optional `notify_team` automation presets are packaged for contract expiry, identity expiry, renewal and employee termination. Messages contain no identifiers. They are tenant-instantiated presets, not automatically executed schedules. Contract state-machine metadata declares draft → active → terminated/completed/renewed; cancellation reason and both termination dates are conditionally required.

The contract entity also ships an enabled `date_tasks` rule for a 30-day HR review. It uses the platform date task worker and Organization Tasks, independently of the optional expiry-day notification preset.

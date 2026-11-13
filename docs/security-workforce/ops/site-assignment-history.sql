-- Apply after record-relation-history.sql in the storage database.
-- Scope the trigger to the app and entity at the database boundary.
CREATE OR REPLACE TRIGGER workforce_site_assignment_history
AFTER INSERT OR UPDATE OF data ON public.storage_entities
FOR EACH ROW
WHEN (
    NEW.solution_id = 'security-workforce-manager'
    AND NEW.collection = 'employee'
    AND NEW.deleted_at IS NULL
)
EXECUTE FUNCTION public.record_relation_history(
    'assigned_site', 'duty_site', 'site_assignment', 'employee_id', 'site_id', 'Asia/Dubai'
);

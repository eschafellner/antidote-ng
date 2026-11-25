from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def ensure_owner_membership(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    project_model = apps.get_model("tracker", "Project")
    membership_model = apps.get_model("tracker", "ProjectMembership")
    alias = schema_editor.connection.alias

    for project_id, owner_id in project_model.objects.using(alias).values_list("pk", "owner_id").iterator():
        membership_model.objects.using(alias).update_or_create(
            project_id=project_id, user_id=owner_id, defaults={"role": "admin"}
        )


class Migration(migrations.Migration):
    dependencies = [("tracker", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="project",
            name="archived_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.RunPython(ensure_owner_membership, migrations.RunPython.noop),
    ]

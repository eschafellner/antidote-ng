# AGENTS.md

Dieses Dokument definiert verbindliche Regeln für jeden Agenten (Mensch oder KI), der an diesem Projekt arbeitet. Es gilt zusätzlich zu jeder aufgabenspezifischen Anweisung – bei Konflikten hat eine explizite Anweisung im jeweiligen Task Vorrang, aber Abweichungen von diesem Dokument sollten aktiv benannt werden.

## Projektüberblick

Leichtgewichtiger, performanter Issue-Tracker als schlanke Jira-Alternative.

**Tech-Stack:**
- Backend: Python 3.12+ (kompatibel mit 3.14), Django 6.x, Django ORM
- DB: SQLite lokal, vorbereitet für PostgreSQL (kein SQLite-spezifisches Verhalten nutzen)
- Frontend-Integration: `django-inertia` + Inertia.js, Vue 3 (`<script setup>`, Composition API)
- Styling: Tailwind CSS 3.x
- Drag-and-Drop: VueDraggable (Sortable.js)


## Architekturprinzipien

- **Service-Layer verpflichtend.** Business-Logik (Permissions, Key-Generierung, Activity-Logging) lebt in `services/`, niemals in Views/Controllern. Views orchestrieren nur.
- **Schlanke Inertia-Props.** Seiten bekommen nur die Daten, die sie brauchen – kein Overfetching, kein REST-Overhead.
- **Multi-Tenancy ist nicht verhandelbar.** Jede Query muss implizit oder explizit nach Projektzugehörigkeit gefiltert sein. Ein User ohne `ProjectMembership` in einem Projekt darf dort niemals Daten sehen oder ändern können. Das gilt für jede neue Query, jeden neuen Endpoint, ausnahmslos.
- **Soft-Delete statt Hard-Delete** für Issues (`is_deleted`/`deleted_at`) aus Audit-Gründen.
- **ActivityLog wird im Service-Layer erzeugt**, nicht über Django-Signals – bessere Testbarkeit und Nachvollziehbarkeit.

## Datenmodell (Referenz)

`Project` · `ProjectMembership` (Rollen: `admin`/`member`/`viewer`) · `ProjectInvitation` · `Issue` · `IssueAttachment` · `Comment` · `ActivityLog`

- Issue-Keys (`PROJ-42`) werden **race-condition-sicher** über `IssueKeyService` generiert (`select_for_update` in Transaktion). Niemals `count() + 1`.
- Issue-Status-Workflow: `todo` → `in_progress` → `review` → `done` / `canceled`.
- `position`-Feld auf `Issue` steuert die manuelle Sortierung innerhalb einer Kanban-Spalte.

## Permission-Matrix

Rollen-Checks laufen ausschließlich über `PermissionService` (z. B. `can_edit_issue(user, issue)`, `can_manage_members(user, project)`, `can_invite(user, project)`). Neue Berechtigungsfragen werden als neue, klar benannte Funktion dort ergänzt – nicht als Inline-`if`-Logik in Views verstreut.

| Aktion | Admin | Member | Viewer |
|---|---|---|---|
| Issues lesen | ✅ | ✅ | ✅ |
| Issues anlegen/bearbeiten | ✅ | ✅ | ❌ |
| Issues löschen | ✅ | ❌ | ❌ |
| Kommentieren | ✅ | ✅ | ❌ |
| Mitglieder einladen/verwalten | ✅ | ❌ | ❌ |
| Projekt-Settings ändern | ✅ | ❌ | ❌ |

## Code-Konventionen

- Antworten/Kommentare/Dokumentation auf Deutsch, **Code, Variablen-, Modell- und Funktionsnamen auf Englisch**.
- Type Hints in allen Python-Funktionen/-Methoden.
- Docstrings für Service-Klassen.
- Keine Platzhalter wie `# ... rest of implementation` – Code muss innerhalb des jeweiligen Aufgaben-Scopes vollständig und lauffähig sein.
- Jede Model-Änderung braucht eine passende, lauffähige Migration.

## Testing

- Jede neue Business-Logik (insbesondere Key-Generierung und Permission-Checks) braucht Unit-Tests (pytest-django oder Django TestCase).
- Pflichtfälle, die immer getestet werden müssen bei Änderungen an Issues/Projects: (a) fortlaufende, eindeutige Keys auch unter parallelen Requests, (b) Viewer kann nicht schreiben, (c) User ohne Membership hat keinen Zugriff auf fremdes Projekt.

## UI-Konventionen (Frontend)

- Kanban-Board: Drag-and-Drop aktualisiert `status`/`position` **optimistisch**, mit Rollback bei Fehler.
- Listenansicht: Filterung/Pagination **serverseitig**, nicht client-seitig über alle Datensätze.
- Issue-Details als Slide-over mit Inline-Editing (Status, Priorität, Assignee), Markdown-Rendering für Beschreibung/Kommentare, Activity-Log-Timeline.

## Arbeitsweise für Agenten

- Vor Beginn einer neuen Aufgabe: prüfen, auf welchen bereits bestehenden Models/Services/Komponenten aufgebaut werden soll – keine parallelen, redundanten Strukturen schaffen.
- Nach Abschluss einer Aufgabe: kurz zusammenfassen, welche Dateien angelegt/geändert wurden und welche TODOs offen sind.
- Scope-Grenzen respektieren: nicht "vorauseilend" Code für spätere Schritte mitliefern, der noch nicht angefordert wurde.

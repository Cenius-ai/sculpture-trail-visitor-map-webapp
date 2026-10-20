# Using the Sculpture Trail Visitor Map

Start the app (`python3 app.py`) and open <http://localhost:8000>.

## Sign in

The sign-in card lists the demo credentials and includes a **Sign in with the curator demo**
button that fills and submits the form in one click.

- Curator: `cenius@cenius.ai` / `cenius`
- Visitor: `visitor@example.com` / `trail1234`

Wrong credentials always produce the same single message so the form never reveals which
accounts exist. Use the **Show/Hide** control beside the password field to check what you typed.

New here? **Create one** on the sign-in card: display name, email, password (8+ characters) and
confirmation. You are signed in immediately and land back on the page you originally asked for.

## The trail map (home)

- **Pins** are projected from each sculpture's stored latitude/longitude onto a local SVG plan.
  Drag to pan, scroll or use **+ / −** to zoom, **Reset view** to return.
- **Click or Tab to a pin** and press Enter to open its popup: title, artist, material, stage,
  and an **Open sculpture** link.
- **Stage filter** (top right of the map) narrows pins, the stage list and the index table to one
  stage. A spinner-free skeleton shows while the request is in flight; if the request fails, a
  banner offers **Try again**. **Show the whole trail** clears the filter.
- The **Stages** panel lists every stage with its accessibility-note preview and piece count.
- The **Index** table lists all sculptures in trail order with artist, material, stage and
  average rating.

## Stage guide

Open a stage from the map panel, the nav bar, or `/stages/:id`. Each guide shows:

- the stage description and its **full accessibility notes** (surface, gradients, widths,
  accessible viewing points),
- every sculpture on that stage **in trail order**, linked to its detail page,
- a static plan of just that stage's sculptures (click a pin to open the piece),
- stage facts (number, piece count, date added).

A stage with no sculptures shows a friendly empty state instead.

## Sculpture detail

`/sculptures/:id` shows the title, artist, material, description, stage name with its
accessibility note, stored coordinates, average rating and the complete feedback list.

**Leave feedback:** choose a star rating (1–5) and write a comment (3–1000 characters), then
**Post feedback**. Your note appears at the top of the list immediately, the average and note
count update in place, and the row flashes green. Reload the page — the note is still there.
Submitting without a rating or a comment shows an inline error at the field and sends nothing.
Double-clicking the submit button cannot create two notes.

Use **View on the map** to jump back to the dashboard with that pin's popup open, or the
**Next on the route** card to walk on to the following piece.

## Curator studio

Sign in as a curator and open **Studio** in the nav bar (`/curator`).

- **Add a sculpture:** title, artist, material, stage, latitude, longitude, description → **Save
  sculpture**. The new row appears in the studio list and its pin appears on the dashboard map
  after a reload.
- **Edit:** press **Edit** on a row. The form fills with that record and switches to edit mode;
  **Cancel edit** clears it. Save to update every page.
- **Delete:** press **Delete** and confirm in the dialog (Cancel or Escape dismisses it). A
  sculpture's feedback is deleted with it.
- **Stages:** the same create/edit/delete flow for stage name, number, description and
  accessibility notes. A stage that still has sculptures assigned refuses to delete and explains
  why — move or delete its sculptures first.
- Validation runs before any request: a latitude of `999` shows *"Latitude must be between -90
  and 90"* at the field and nothing is sent. Server-side validation mirrors every rule.

Visitors who open `/curator` see an explanatory page and can still browse the whole trail; every
write endpoint also rejects them with `403` if called directly.

## Command palette

Press **⌘K** / **Ctrl+K** (or **Jump to** in the top bar) to open the palette. Type to fuzzy
filter pages, stages and sculptures, move with ↑/↓, press Enter to open, Escape to close.

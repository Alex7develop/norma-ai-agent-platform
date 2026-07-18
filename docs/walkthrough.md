# Product walkthrough

End-to-end path through the Norma AI MVP. Use this after `docker compose up`
and `npm run dev` in `frontend/` (see [development.md](development.md)).

## 1. Register and sign in

1. Open `http://localhost:5173`.
2. Create an account (email + password) or sign in.
3. You land in **Assistant** with a default workspace, project, and knowledge
   space in the sidebar.

Expected: sidebar shows workspace email, project/space selectors, and
Assistant / Workflows / Knowledge.

## 2. Add knowledge

1. Open **Knowledge**.
2. Upload a PDF, DOCX, Markdown, or TXT (or connect Notion and import pages).
3. Wait until the document status badge shows **completed** (pending → completed).

Expected: the document appears in the list with chunk count; Assistant can
ground answers on it.

## 3. Ask the Assistant

1. Open **Assistant**.
2. Start a **New chat** (or continue an existing thread from the list).
3. Ask a question about the uploaded material.

Expected: grounded answer with source chips. On narrow screens, use the menu
button to open navigation.

## 4. Run a workflow

1. Open **Workflows**.
2. Pick **Launch Strategy** (full pack) or **Research Brief** (retrieve →
   research → persist).
3. Enter a brief (optional product name) and run.

Expected: pipeline steps advance while the worker runs; history lists the run;
artifacts open in the reader when complete.

## 5. Inspect artifacts and knowledge

1. Select artifacts (research, pack, …) in the workflow panel.
2. Return to **Knowledge** — the persisted pack/brief appears as a document.

Expected: workflow output is searchable by the Assistant like any other upload.

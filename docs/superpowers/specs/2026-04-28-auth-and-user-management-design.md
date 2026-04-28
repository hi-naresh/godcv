# Auth & User Management — Design

**Status:** Draft for review
**Date:** 2026-04-28
**Scope:** Add multi-user authentication and user management to GodCV. Replace the
hardcoded `profile_id = 1` model with per-user data isolation behind cookie sessions.

---

## Goal

GodCV today is single-user: every API call resolves to the row in `profiles` with
`id = 1`. To make the app a multi-user SaaS, we need a real concept of `users`,
sessions, registration, login, logout, and per-user data isolation across every
existing router.

## Non-Goals (v1)

- Email verification, password reset, magic links — no email infrastructure.
- OAuth (Google, GitHub, etc.).
- MFA, account lockout, login rate limiting, audit log.
- Password complexity rules beyond an 8-character minimum.
- "Remember me" toggle, sliding session renewal, "log out everywhere" UI.
- Multiple profiles per user (the schema permits it; the UI does not expose it).
- Admin / RBAC. Every user is equal.
- Account deletion endpoint (data isolation is in place; the explicit DELETE flow
  can come later).
- CSRF tokens (relying on `SameSite=Lax`).

## Decisions Locked Before Design

These were resolved during brainstorming:

1. **Deployment model:** multi-user SaaS (anyone can sign up).
2. **Auth method:** email + password only.
3. **Session strategy:** opaque token in an `HttpOnly` cookie, server-side `sessions`
   table.
4. **Email features:** none. No verification, no password reset.
5. **Existing data:** wipe `profiles`, `role_insights`, `saved_cvs`, and
   `tailoring_history` on the first auth-enabled deploy. New users seed via an
   onboarding flow that prompts for a master resume in markdown.

## Architecture

```
Browser  ──[email + password]──▶  POST /api/auth/register
                                  POST /api/auth/login
                                          │
                                          ▼ creates row in `sessions`,
                                            sets HttpOnly cookie
                                            `godcv_session=<token>`
                                          │
Browser  ──[every API call w/ cookie]──▶  FastAPI dependency
                                          `current_user(request)`
                                          │ reads cookie → SELECT session →
                                          │ returns User or raises 401
                                          ▼
                                     existing routers (profile, tailor, jobs,
                                     export, saved_cvs) — all use
                                     current_user.id instead of profile_id=1
```

Two new modules:

- `backend/services/auth.py` — password hashing, session lifecycle, the
  `current_user` FastAPI dependency.
- `backend/routers/auth.py` — register, login, logout, me endpoints.

## Data Model

### New: `users`

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_email ON users(email);
```

### New: `sessions`

```sql
CREATE TABLE sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_sessions_user ON sessions(user_id);
```

`token` is generated server-side via `secrets.token_urlsafe(32)`. Lifetime is 30
days from creation. No sliding renewal.

### Modified: `profiles`

Add a column and a unique index:

```sql
ALTER TABLE profiles ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
CREATE UNIQUE INDEX idx_profiles_user ON profiles(user_id);
```

The unique index enforces 1 user → 1 profile for v1. The schema can support 1:N
later without further migration.

### Wipe migration

Implemented in `db/database.py:_init_tables` alongside the existing idempotent
`ALTER TABLE … ADD COLUMN` migrations:

1. Detect: `users` table does not exist AND `profiles` has rows.
2. Action: `DELETE FROM tailoring_history; DELETE FROM role_insights; DELETE
   FROM saved_cvs; DELETE FROM profiles;`
3. Then create `users`, create `sessions`, add `user_id` column to `profiles`,
   create `idx_profiles_user`.

Once auth is in, every row in `profiles`, `role_insights`, `saved_cvs`,
`tailoring_history` is reachable from a user via `profiles.user_id`. No orphaned
rows are possible because the wipe + UNIQUE constraint enforce it from the start.

The existing auto-seed-from-`resume.md` logic in `routers/profile.py:13-31` is
removed; new users seed via the onboarding flow.

## API Surface

### New auth router (`backend/routers/auth.py`, prefix `/api/auth`)

| Method | Path                  | Body                  | Returns                                          | Notes |
|--------|-----------------------|-----------------------|--------------------------------------------------|-------|
| POST   | `/api/auth/register`  | `{email, password}`   | `{user: {id, email}, needs_onboarding: true}`    | 409 if email taken. Validates email format and password length ≥ 8. Creates user, creates session, sets cookie. |
| POST   | `/api/auth/login`     | `{email, password}`   | `{user: {id, email}, needs_onboarding: bool}`    | 401 on bad creds with a generic message; identical body for unknown email and wrong password. Sets cookie. `needs_onboarding=true` if no profile row exists for the user yet. |
| POST   | `/api/auth/logout`    | (cookie)              | `{ok: true}`                                     | Deletes session row, clears cookie. Idempotent — always 200. |
| GET    | `/api/auth/me`        | (cookie)              | `{user, needs_onboarding}` or 401                 | Used by frontend on app boot to restore session. |

### Modified existing endpoints

All become user-scoped via `Depends(current_user)`:

| Endpoint                                  | Change |
|-------------------------------------------|--------|
| `GET /api/profile`                        | Returns 404 with `{"detail": {"code": "needs_onboarding"}}` if user has no profile yet. No more auto-seed from `resume.md`. |
| `POST /api/profile`                       | Creates the profile **for the authenticated user** — this is the onboarding submission. 409 if user already has a profile. |
| `PUT /api/profile`                        | Updates the authenticated user's profile. |
| `GET /api/profile/insights`               | Filters to current user's profile. |
| `DELETE /api/profile/insights/:id`        | Verifies the insight belongs to current user. 404 (not 403) if not. |
| `POST /api/profile/reset`                 | Wipes only the current user's data, not the global DB. |
| `POST /api/tailor`, `/api/execute`, `/api/jobs/*`, `/api/export/*`, `/api/saved-cvs/*` | Resolve current user from session, filter to their data. |
| `GET /api/models`, `POST /api/models/select` | Use current user's `gemini_api_key`. |
| `GET /api/health`                         | **Stays public** — no auth required. |
| `GET /api/onboarding/template`            | **New, public** — returns `{markdown: "..."}` read from `data/template.md`. Used by the onboarding "Use template" link. |
| `GET /api/usage`                          | Behind auth (it leaks model usage). |

**Authorization on resource IDs** — when a route takes an ID
(`DELETE /api/profile/insights/{id}`, saved-cv routes, history routes), the
service-layer query gets a `WHERE id = ? AND profile_id = ?` clause. Mismatch
returns 404, not 403, to avoid leaking existence.

## Auth Middleware

`backend/services/auth.py` exports:

```python
def hash_password(plain: str) -> str             # passlib bcrypt, cost 12
def verify_password(plain, hashed) -> bool

async def create_session(user_id: int) -> str    # secrets.token_urlsafe(32)
async def revoke_session(token: str) -> None
async def get_session_user(token: str) -> dict | None
    # SELECT joining sessions + users; checks expires_at > now;
    # bumps last_used_at; returns user dict or None

async def current_user(request: Request) -> dict:
    token = request.cookies.get("godcv_session")
    if not token:
        raise HTTPException(401, "Not authenticated")
    user = await get_session_user(token)
    if not user:
        raise HTTPException(401, "Session expired or invalid")
    return user

async def current_user_optional(request: Request) -> dict | None:
    # Same but returns None instead of raising. No current consumer; included
    # for cheap future use.
```

Wiring per protected endpoint:

```python
@router.get("")
async def get_profile(user: dict = Depends(current_user)):
    p = await profile_service.get_profile_by_user(user["id"])
    if not p:
        raise HTTPException(404, detail={"code": "needs_onboarding"})
    return p
```

### Cookie attributes

Set on register and login responses:

```
godcv_session=<token>; HttpOnly; SameSite=Lax; Path=/; Max-Age=2592000
```

`Secure` is added in production via env var `GODCV_COOKIE_SECURE=1`. Off in dev so
`http://localhost` works.

`SameSite=Lax` blocks cross-site CSRF on state-changing POSTs. No separate CSRF
token machinery in v1.

### Session cleanup

A one-liner in the existing `lifespan` startup in `main.py:16`:

```python
DELETE FROM sessions WHERE expires_at < datetime('now')
```

No background job, no cron. Stale tokens fail validation anyway.

## Frontend

### New views

| File                          | Purpose |
|-------------------------------|---------|
| `views/LoginView.vue`         | Email + password form. On success → `router.push('/')` (or `/onboarding` if `needs_onboarding`). Link to `/register`. |
| `views/RegisterView.vue`      | Email + password (with confirm) form. On success → `router.push('/onboarding')`. Link to `/login`. Includes a clear notice that there is no password recovery in v1. |
| `views/OnboardingView.vue`    | Single-step form: large textarea for master resume markdown + a "Name" field + a "Save & Continue" button. Submits `POST /api/profile`. On success → `router.push('/')`. Includes a "Use template" link that fetches `GET /api/onboarding/template` (a new public endpoint returning `{markdown: "..."}` from `data/template.md`) so users have something to start from. |

### New store

```ts
// stores/auth.ts (Pinia)
state: { user, isAuthenticated, needsOnboarding, loading }
actions: register(email, password), login(email, password),
         logout(), checkSession()  // calls GET /api/auth/me
```

### Router additions

```ts
// router.ts — add three routes
{ path: '/login',      component: () => import('./views/LoginView.vue'),      meta: { public: true } },
{ path: '/register',   component: () => import('./views/RegisterView.vue'),   meta: { public: true } },
{ path: '/onboarding', component: () => import('./views/OnboardingView.vue'), meta: { requiresAuth: true } },
```

### Global navigation guard

Added to `router.ts`:

- If route is `public` → allow.
- Otherwise: ensure `auth.checkSession()` has run; if `!isAuthenticated` → redirect
  `/login`.
- If authenticated but `needsOnboarding` and not on `/onboarding` → redirect
  `/onboarding`.
- If authenticated, has profile, and on `/login`, `/register`, or `/onboarding` →
  redirect `/`.

### App boot

In `main.ts` / `App.vue`, call `auth.checkSession()` once before the first route
resolves. Show a brief loading state.

### Fetch / cookie config

Every API call must include the cookie:

- For `fetch`: add `credentials: 'include'` to all calls in `composables/*.ts`
  (currently 7 files: `useJobs.ts`, `useMarkdown.ts`, `useProfile.ts`,
  `useSavedCVs.ts`, `useSeniority.ts`, `useTailor.ts`, `useToast.ts`).
- Backend CORS already has `allow_credentials=True` and explicit
  `allow_origins=["http://localhost:3000"]` — both correct.

### Global 401 handling

Add a small fetch wrapper in a new `utils/api.ts` that all composables use; on
401 it clears the auth store and pushes `/login`. Keeps 401 handling out of
each composable.

### Shell UI

The existing nav (Editor, Profile, History, Preferences, Roles, Saved CVs) is
hidden on `/login`, `/register`, and `/onboarding`. Add an Account menu (showing
logged-in email + a "Log out" button) to the top bar when authenticated.

## Security Details

- **Passwords:** `passlib[bcrypt]` (added to `requirements.txt`), cost factor 12.
  Min length 8 enforced server-side. Max length 72 bytes (bcrypt's hard limit) —
  longer passwords rejected with a clear error. Passwords are never logged or
  returned in responses.
- **Session token:** `secrets.token_urlsafe(32)` → 43-char URL-safe random
  string. Stored as plaintext (it is already a high-entropy bearer secret;
  hashing buys nothing because DB read is needed regardless).
- **Cookie:** `HttpOnly; SameSite=Lax; Path=/; Max-Age=2592000`; `Secure` in prod
  via `GODCV_COOKIE_SECURE=1`. Cookie name: `godcv_session`.
- **Email storage:** case-insensitive (`COLLATE NOCASE`), trimmed on input.
  Format-validated by Pydantic `EmailStr` (requires `email-validator` package,
  added to `requirements.txt`). Uniqueness enforced by DB constraint — duplicate
  registrations get a 409 from a `try/except IntegrityError`, not a TOCTOU
  pre-check.
- **Login error message:** identical body for unknown email vs wrong password
  (`{"detail": "Invalid email or password"}`) to prevent user enumeration. Equal
  timing isn't enforced (would require dummy hashing on the unknown-email
  branch); a weak side channel remains. Acceptable for v1.
- **Logout:** always 200, even with no/invalid cookie. Always emits
  `Set-Cookie: godcv_session=; Max-Age=0; Path=/`.
- **Authorization on resource IDs:** service-layer queries on `saved_cvs`,
  `tailoring_history`, `role_insights` always filter by `profile_id` derived
  from `current_user`. 404 (not 403) on mismatch.
- **Logging:** auth events (register success, login success, login failure with
  email, logout) at INFO with the email but never the password. Session tokens
  never in logs.

## Risks Accepted for v1

- **Login brute force** — no rate limiting. Mitigation later via `slowapi` or
  fronting nginx. Acceptable on a launch with low traffic.
- **Lost passwords = lost accounts** — no email means no recovery path.
  Onboarding/login UI must warn the user explicitly.
- **Timing side channel on `/login`** — small, not enforced equal-time.
- **Single-device session model** — listing/revoking sessions per device is
  post-v1.

## Tests

Added to existing `tests/` dir, pytest.

### `tests/test_auth.py`

- Register: valid email + password → 200, returns user, sets cookie.
- Register: duplicate email → 409.
- Register: invalid email format → 422; password < 8 → 400.
- Login: correct creds → 200, sets cookie. Bad creds → 401 with generic message.
  Unknown email → 401 with the same message and body.
- Logout: with valid cookie → 200, session row deleted. Without cookie → still
  200.
- `/me`: with valid cookie → user. Without → 401. With expired session → 401.

### `tests/test_auth_isolation.py`

- Two users register; user A's `GET /api/profile` cannot see user B's data.
  `DELETE /api/profile/insights/{B_insight_id}` from user A returns 404.
- User A creates a saved-cv; user B's `GET /api/saved-cvs` does not include it.
  `GET /api/saved-cvs/{A_id}` from user B returns 404.

### `tests/test_onboarding.py`

- Fresh registered user: `GET /api/profile` returns 404 with
  `{"code": "needs_onboarding"}`.
- `POST /api/profile` succeeds once, second call returns 409.
- After onboarding, `/api/auth/me` returns `needs_onboarding=false`.

### Existing tests

Any test that hits a router will need a session cookie helper (`auth_client`
fixture).

## Manual QA Checklist (frontend)

- Register → land on `/onboarding`.
- Submit master resume markdown → land on `/`.
- Hard refresh on `/` → still logged in (session cookie persists).
- Click "Log out" → redirected to `/login`, can't reach `/` anymore.
- Register a second account in an incognito window → only sees own data.
- `GET /api/profile` from a tool with no cookie → 401.

## File-Touch Summary

**New files:**
- `backend/services/auth.py`
- `backend/routers/auth.py`
- `frontend/src/stores/auth.ts`
- `frontend/src/views/LoginView.vue`
- `frontend/src/views/RegisterView.vue`
- `frontend/src/views/OnboardingView.vue`
- `frontend/src/utils/api.ts`
- `tests/test_auth.py`
- `tests/test_auth_isolation.py`
- `tests/test_onboarding.py`

**Modified files:**
- `backend/db/database.py` (new tables, wipe migration)
- `backend/db/models.py` (Pydantic models for register/login/user)
- `backend/main.py` (mount auth router; cookie-secure config; protect `/api/usage`,
  `/api/models`, `/api/models/select`)
- `backend/routers/profile.py` (Depends(current_user); remove auto-seed; per-user
  scoping)
- `backend/routers/tailor.py` (Depends(current_user); per-user scoping)
- `backend/routers/jobs.py` (Depends(current_user); per-user scoping)
- `backend/routers/export.py` (Depends(current_user))
- `backend/routers/saved_cvs.py` (Depends(current_user); per-user scoping)
- `backend/services/profile.py` (`get_profile_by_user`, scoped variants of
  insights / history / saved-cv lookups)
- `frontend/src/router.ts` (new routes + global guard)
- `frontend/src/main.ts` or `App.vue` (boot-time `checkSession`)
- `frontend/src/composables/*.ts` (use new API wrapper with
  `credentials: 'include'` and 401 handling) — 7 files
- `requirements.txt` (`passlib[bcrypt]`, `email-validator`)

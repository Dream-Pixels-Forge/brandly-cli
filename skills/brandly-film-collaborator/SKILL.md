---
name: brandly-film-collaborator
description: >
  Multi-person film collaboration via git with automatic role enforcement. Lead creates repo and assigns roles; skill enforces file ownership — Image Director (still plates), Video Director (takes), Assembly Director (edit/exports), Audio Director (sound) — refusing cross-role edits. Provides folder structure, minimal git commands, role definitions, Lead-only ops, invitation flow, conflict resolution. For brandly-cli projects the roles map onto the `.brandly/<project>/` tree (see the mapping table inside). Trigger for team film production, distributed filmmaking, splitting film work across people, git for film projects. NOT for solo filmmaking or non-film collaboration.
---

# Brandly Film Collaborator — Multi-Person AI Filmmaking

Divide AI film production across a team using git. One person owns stills. Another owns video. Another owns assembly. Everyone works from the same canon. No headache.

> "A film is never made alone. AI filmmaking shouldn't be either."

---

## FIRST: Role Detection — Who Are You?

**Before doing anything else,** determine your identity in this project. This is how the skill prevents conflicts when multiple team members use it simultaneously.

### Step 1: Are you in a project directory?

```bash
git rev-parse --show-toplevel 2>$null
```

If this returns nothing: you are not in a film project repo. Ask if the user wants to **become the Lead and create one**, or if they should **clone an existing project from the Lead**.

### Step 2: If this is a new project — you are the Lead

If no git repo exists and the user wants to start a film project:

1. The current user is the **Lead**. Only the Lead creates the repo.
2. The Lead chooses the team size, assigns roles, and writes `README.md`.
3. The Lead creates the repo, pushes it, and shares the clone URL with the team.
4. The Lead is the only person who can add/change role assignments in `README.md`.

**The Lead CAN hold any role** (including all of them for solo work). The Lead is the director who builds the team.

### Step 3: If this is an existing project — detect your assigned role

If a git repo already exists, read `README.md` and extract the team roster:

```bash
# Check the project README for role assignments
git pull
```

Then read `README.md`. Look for the team roster section:

```markdown
## Team

- **Lead:** @lead-username (Roles A, B, C, D)
- **@alice** — Role A (Image Director)
- **@bob** — Role B (Video Director)
- **@carol** — Role C (Assembly Director)
- **@dave** — Role D (Audio Director)
```

**Identify your git username** with:

```bash
git config user.name
```

If this returns nothing: `git config user.name` is not set. Set it now — it's how the skill identifies you. Use the same `@username` that will appear in README.md:

```bash
git config user.name "your-username"
```

Match your username against the team roster. This tells you:

- **Your assigned role(s)** — what you are allowed to touch
- **Your file ownership** — which directories are yours
- **Who owns the other directories** — don't touch those

### Step 4: Enforce your role

Once your role is identified, the skill enforces file ownership:

| Role         | You CAN touch        | You CANNOT touch                            |
| ------------ | -------------------- | ------------------------------------------- |
| A (Image)    | `canon/`             | `shots/`, `assembly/`, `audio/`             |
| B (Video)    | `shots/`, `renders/` | `canon/` (read-only), `assembly/`, `audio/` |
| C (Assembly) | `assembly/`          | `canon/` (read-only), `shots/`, `audio/`    |
| D (Audio)    | `audio/`             | `canon/` (read-only), `shots/`, `assembly/` |
| Lead         | Everything           | Nothing restricted                          |

**If you are not the Lead and your role is not found in README.md:** stop. Tell the user: "You are not listed in this project's team roster. Contact the Lead (@lead-username) to be assigned a role. Do not make changes until your role is assigned."

**If a task is requested that belongs to another role:** tell the user: "That task belongs to [Role X], assigned to @person. You are [Your Role]. I can help you with tasks in your domain. Would you like me to add a request for @person to the task board instead?"

---

## Lead-Only Operations

Only the Lead can:

| Operation                                          | Why only the Lead                          |
| -------------------------------------------------- | ------------------------------------------ |
| Create the repo                                    | One source of truth from day one           |
| Change role assignments in `README.md`             | Prevents two people claiming the same role |
| Add or remove team members                         | Controlled access                          |
| Change folder structure or naming conventions      | Consistency across all clones              |
| Resolve conflicts in shared files (e.g., tasks.md) | Final authority on what ships              |
| Mark the film as complete                          | Official sign-off                          |

### Lead: Inviting Team Members

When the Lead wants to add someone:

1. Tell the new member the repo clone URL
2. Tell them their assigned role: "You are Role B — Video Director"
3. Update `README.md` with their `@username` and role
4. Commit: `[LEAD] add @username as Role B`
5. Push
6. The new member clones, and their skill auto-detects their role on first run

### Lead: Reassigning Roles

If someone leaves or roles need to shift:

1. The Lead edits `README.md` team roster
2. Commits: `[LEAD] reassign roles: @alice now B, @carol now A+B`
3. Pushes
4. Everyone pulls — their skill re-reads `README.md` and respects the new assignment

---

## The `README.md` Template (Lead Creates This)

This is the exact format. The skill parses it to detect roles. The Lead fills in the bracketed values.

```markdown
# [FILM TITLE]

**Premise:** [One sentence — the reason this film exists.]

**Status:** [Pre-production / In Production / Assembly / Audio / Complete]

**Repo:** [clone URL]

---

## Team

- **Lead:** @[lead-username] ([Lead's roles: A, B, C, D or specific])
- **@[username1]** — Role A (Image Director)
- **@[username2]** — Role B (Video Director)
- **@[username3]** — Role C (Assembly Director)
- **@[username4]** — Role D (Audio Director)

---

## Model & Target

- **Primary model:** [Hailuo 2.3 / Kling 3.0 / Seedance 1.5 Pro / Veo 3.1 / Sora 2 / Runway Gen-4.5]
- **Aspect ratio:** [16:9 / 9:16 / 2.39:1]
- **Total duration:** [estimated minutes]

---

## Cloud Sync

- **Renders sync via:** [Google Drive / Dropbox / MEGA / Syncthing]
- **Link:** [shared folder URL — Lead shares with team separately]

---

## Phase

- [ ] Phase 1: Foundation (canon created, shotlist drafted)
- [ ] Phase 2: Shot Planning (shotlist approved)
- [ ] Phase 3: Parallel Generation (stills + video in progress)
- [ ] Phase 4: Assembly (rough cut in progress)
- [ ] Phase 5: Audio + Polish (final mix in progress)
```

**The skill reads the `## Team` section** to detect the current user's role. The `@username` must match `git config user.name`. If it doesn't match, the skill refuses to proceed.

---

## The Project Structure

Every collaborator clones this exact structure. Nothing else. Consistency is the collaboration.

> **brandly-cli projects:** when the film is produced with brandly-cli, map the
> same roles onto the `.brandly/<project>/` tree instead of `canon/`/`shots/`:
>
> | Role | Owns (brandly tree) |
> |------|---------------------|
> | Image Director | `images/` (reference plates via `brandly reference`) |
> | Video Director | `videos/scenes/`, `videos/transition/` (via `brandly produce`) |
> | Assembly Director | `export/`, assembly via `brandly stitch` / `brandly export` |
> | Audio Director | `audio/` (via `brandly audio` / MiniMax) |
>
> `docs/plan/production_plan.md` is the single source of truth (the `canon/`
> equivalent) — every generation registers there.

```
film-project/
├── README.md              ← Film title, premise (one sentence), team roster, status
├── .gitignore             ← Ignore large video renders, temp files
├── canon/                 ← SINGLE SOURCE OF TRUTH — everyone works from these
│   ├── characters/
│   │   ├── protagonist-front.png
│   │   ├── protagonist-3-4.png
│   │   ├── protagonist-profile.png
│   │   └── antagonist-front.png
│   ├── environments/
│   │   ├── location-A-wide.png
│   │   ├── location-B-wide.png
│   │   └── location-C-wide.png
│   ├── style/
│   │   ├── color-palette.png
│   │   └── lighting-reference.png
│   └── keyframes/         ← Start/end frames for image-to-video shots
│       ├── shot-01-start.png
│       ├── shot-01-end.png
│       └── shot-02-start.png
├── shots/                 ← PROMPTS — text, always tracked in git
│   ├── shot-01.md
│   ├── shot-02.md
│   └── ...
├── renders/               ← GENERATED VIDEO — gitignored (too large), shared via cloud or local sync
│   ├── shot-01/
│   │   ├── take-01.mp4
│   │   ├── take-02.mp4
│   │   └── selected.mp4   ← symlink/copy of the chosen take
│   └── shot-02/
├── audio/                 ← AUDIO ASSETS
│   ├── voice/
│   ├── sfx/
│   ├── music/
│   └── audio-plan.md      ← Audio strategy document
├── assembly/              ← FINAL CUT
│   ├── timeline.md        ← Edit decision list
│   ├── rough-cut.mp4
│   └── final.mp4
└── tasks.md               ← WHO IS DOING WHAT — the living task board
```

---

## The Four Roles

One person can hold multiple roles, but each role has one owner at a time. No two people touch the same file simultaneously.

### Role A: Image Director

**Owns:** `canon/`, `canon/keyframes/`
**Does:** Generates character portraits, environment references, style references, keyframes. These are the foundation everything else builds on.
**Hands off to:** Role B (Video Director)
**Skills to use:** Midjourney, DALL-E, Flux, Stable Diffusion, ComfyUI
**Git convention:** Always push canon assets first. Others pull before starting work.

### Role B: Video Director

**Owns:** `shots/`, `renders/`
**Does:** Reads canon images → writes prompts in `shots/` → generates video → saves to `renders/` → marks the selected take.
**Hands off to:** Role C (Assembly Director)
**Skills to use:** `dpf-continue-action-film`, `dpf-film-director`, `hailuo-prompting`, `kling-prompting`, `ai-video-generation`
**Git convention:** Push prompts immediately (text, small). Renders go to cloud (too large for git).

### Role C: Assembly Director

**Owns:** `assembly/`
**Does:** Takes selected renders from Role B → edits sequence → color grades → adds transitions → exports rough cut → iterates with team → exports final.
**Hands off to:** Role D (Audio Director) or back to team for review
**Skills to use:** DaVinci Resolve, Premiere Pro, After Effects, `dpf-senior-editor`, `dpf-senior-motion-designer`

### Role D: Audio Director

**Owns:** `audio/`
**Does:** Voice generation, SFX, foley, music score, final mix. Can work in parallel with Role C if audio plan is locked.
**Skills to use:** MiniMax Speech 2.8, MiniMax Music 2.6, ElevenLabs, Suno, `audio-pro`, `ai-video-generation` (foley)

---

## The Git Workflow — No Headache

**Role enforcement is automatic.** When the skill is active, it knows your role from `README.md`. It will refuse to modify files outside your role's ownership.

**All git commands below work on Windows (PowerShell), macOS, and Linux.** The skill adapts the commands to your environment — use them as shown.

These are the ONLY commands anyone needs. Nothing else.

### Lead Setup — Create the Repo (Lead Only)

```bash
# The Lead creates the project. No one else does this.
mkdir film-project
cd film-project
git init
# Create the folder structure (see above)
# Write README.md using the template
# Create .gitignore
git add .
git commit -m "[LEAD] init: film project scaffold, team roster"
# Create the GitHub/GitLab repo, then:
git remote add origin <repo-url>
git push -u origin main
# Share the clone URL with the team.
```

### Team Member Setup — Clone and Join (Non-Lead)

```bash
# Anyone who is NOT the Lead
git clone <repo-url>
cd film-project
# That's it. On first run, the skill reads README.md,
# finds your @username, and knows your role.
```

### .gitignore (Create This First)

```
# Large binary files — don't track in git
renders/
assembly/rough-cut.mp4
assembly/final.mp4
*.mp4
*.mov
*.wav
*.mp3

# Temp files
*.tmp
.DS_Store
Thumbs.db
```

### Daily Commands (Everyone)

```bash
# START OF SESSION — get latest, re-check your role
git pull
# The skill re-reads README.md after pull to confirm your role hasn't changed

# WORK — only in directories your role owns (see Role Detection table above)
# The skill enforces this — if you try to touch another role's files, it refuses

# END OF SESSION — share your work
git add .                          # Only stages files in YOUR role's directories
git commit -m "[ROLE] description" # Role tag is mandatory
git push

# Done. That's it.
```

### Commit Message Convention

Every commit follows this pattern:

```
[ROLE] short description

Role tags: [A] [B] [C] [D] [LEAD]

Examples:
[LEAD] init: film project scaffold, assign team roles
[LEAD] add @dave as Role D
[A] add protagonist character portraits
[A] update environment reference — location B
[B] shot-01 prompt + selected take
[B] shot-03: 5 takes generated, take-03 selected
[C] rough cut v2 — reordered shots 2 and 3
[D] add voiceover for protagonist
[D] add background score — tension cue
```

### Conflict Resolution — The Only Rule

**Never edit the same file at the same time.** If two people need to touch the same thing:

1. One person finishes and pushes first
2. The other person pulls, then works

If git complains about a conflict (rare if you follow the roles):

```bash
# Your changes conflict with remote. Save your work somewhere safe.
git stash
git pull
git stash pop
# Check for conflicts:
git status
# If status shows "both modified" — resolve manually.
# Keep both people's work, don't delete anything.
# After resolving:
git add .
git commit -m "merge: resolve conflict in [file]"
git push
```

---

## Collaboration Workflow: Scene by Scene

### Phase 1: Foundation (Everyone Together)

1. **Team agrees on premise.** One sentence. Written in `README.md`.
2. **Team agrees on roles.** Who is A, B, C, D? Written in `README.md`.
3. **Role A starts immediately** — generates character and environment references. Pushes to `canon/`.
4. **Everyone else pulls** — now everyone has the same visual reference.

### Phase 2: Shot Planning (Role B Leads)

5. **Role B writes the shotlist** — one `.md` file per shot in `shots/`. Each file contains the prompt, model, duration, and which canon images it references.
6. **Team reviews shotlist** — comments on the PR or directly in chat. Revise until approved.

### Phase 3: Parallel Generation (Roles A + B)

7. **Role A generates keyframes** for image-to-video shots. Pushes to `canon/keyframes/`.
8. **Role B generates video** — for each shot, generates multiple takes. Saves to `renders/`. Marks the selected take by creating a `selected.mp4` symlink or copy.
9. **Role A continues** generating any additional references needed.

### Phase 4: Assembly (Role C)

10. **Role C pulls all selected renders** (from cloud storage — renders are gitignored).
11. **Role C assembles rough cut** — writes `assembly/timeline.md` (edit decision list), exports `rough-cut.mp4`.
12. **Team reviews rough cut** — feedback collected in `tasks.md` or chat.

### Phase 5: Audio + Polish (Roles C + D in Parallel)

13. **Role D starts audio** once rough cut timing is locked. Generates voice, SFX, music. Saves to `audio/`.
14. **Role C iterates on picture** — color grade, transitions, compositing.
15. **Roles C + D sync** — Role C sends latest picture to Role D. Role D syncs audio to picture.
16. **Final mix** — picture + audio together. Export `final.mp4`.

---

## Cloud Storage Integration

Git tracks text (prompts, plans, tasks). Cloud storage handles binaries (video renders, audio files, large images). Both live in the same project folder — they don't conflict. One folder. Two systems. Zero headache.

### Setup Pattern (Same for Every Service)

The project folder itself lives inside a synced cloud folder. Git tracks text files inside it. Cloud sync handles the heavy binaries.

```
Cloud-synced folder (Google Drive / OneDrive / MEGA / Dropbox)
└── film-project/          ← This IS the cloud folder AND the git repo
    ├── .git/              ← Git objects (gitignored from cloud sync)
    ├── .gitignore         ← Excludes renders/ and audio/ from GIT only
    ├── canon/             ← Images — git-tracked (small) + cloud-backed (safe)
    ├── shots/             ← Text prompts — git only
    ├── renders/           ← Video files — cloud sync only (gitignored)
    ├── audio/             ← Audio files — cloud sync only (gitignored)
    ├── assembly/          ← Timeline docs (git) + exports (cloud only)
    └── tasks.md           ← Task board — git only
```

**How it works:**

- `git` ignores `renders/`, `audio/`, and `.mp4`/`.mov`/`.wav`/`.mp3` files (via `.gitignore`)
- Cloud sync syncs EVERYTHING in the folder (including git-tracked files — harmless redundancy)
- Role B drops a render in `renders/shot-01/take-03.mp4` → cloud sync uploads it → Role C's cloud sync downloads it → Role C has the file instantly
- No manual upload/download. No separate cloud UI. Just save the file.

### Lead Setup (One-Time)

1. Choose a cloud service (see comparison below)
2. Create a shared folder in that service called `[film-name]-project`
3. Share the folder with all team members (give edit access)
4. Inside the shared folder, create the project: `git init`, scaffold, etc.
5. The project now lives at e.g. `C:\Users\You\GoogleDrive\[film-name]-project\`
6. Share the git clone URL (GitHub/GitLab) AND confirm everyone has cloud folder access

### Team Member Setup

1. Accept the cloud folder share → sync client downloads it locally
2. Open a terminal inside the synced folder
3. `git clone <repo-url> .` (clone into the existing synced folder) — or, if the Lead already pushed:
   ```bash
   git init
   git remote add origin <repo-url>
   git pull origin main
   ```
4. Both systems are now active: git for text, cloud for binaries

### Daily Flow

```
You save a render in renders/ → cloud sync uploads automatically
Team member's cloud sync downloads automatically → they have the file
No one thinks about it. It just works.
```

---

## Cloud Service Guide

### Google Drive

**Best for:** Teams already using Google Workspace. Free 15 GB per user. Reliable, ubiquitous.

**Setup:**

1. Install [Google Drive for Desktop](https://www.google.com/drive/download/)
2. During setup, choose **"Stream files"** (saves disk space) or **"Mirror files"** (always available offline — recommended for video work)
3. Create a folder in Google Drive → right-click → Share → add team emails with Editor access
4. The folder appears locally at:
   - **Windows:** `G:\Shared drives\[folder]` (stream) or `C:\Users\You\Google Drive\[folder]` (mirror)
   - **macOS:** `/Users/You/Google Drive/[folder]`
5. Create the film project inside this folder

**Caveats:**

- Google Drive sometimes throttles large uploads. For 500MB+ video renders, give it time.
- "Stream files" mode can cause delays if a render isn't cached locally. Mirror mode preferred.
- Google Drive shared folder limits: 400,000 items max. A film project won't hit this.

**Sync speed:** Good. ~50-100 Mbps typical. Large renders (1GB+) may take 5-15 minutes.

---

### OneDrive

**Best for:** Teams on Microsoft 365. 1 TB included with most plans. Deep Windows integration.

**Setup:**

1. OneDrive is built into Windows 10/11. On macOS, install from the App Store.
2. Create a folder in OneDrive → right-click → Share → add team emails
3. The folder appears locally at:
   - **Windows:** `C:\Users\You\OneDrive\[folder]`
   - **macOS:** `/Users/You/OneDrive/[folder]`
4. Create the film project inside this folder
5. Right-click the project folder → **"Always keep on this device"** (prevents files from being offloaded)

**Caveats:**

- OneDrive's "Files On-Demand" can offload rarely-used files. For renders and audio that Role C needs, this causes delays. Use "Always keep on this device" for the project folder.
- Personal OneDrive vs OneDrive for Business have different sharing models. Business is better for teams.
- Sync conflicts are rare but possible if two people edit the same binary simultaneously — which shouldn't happen with role enforcement.

**Sync speed:** Excellent on Windows. ~100-200 Mbps. Deep OS integration means near-instant sync.

---

### MEGA

**Best for:** Privacy-focused teams. 20 GB free. End-to-end encrypted. Generous free tier.

**Setup:**

1. Install [MEGAsync](https://mega.io/desktop)
2. Create a folder in MEGA → right-click → Share → add team emails
3. During MEGAsync setup, set the sync folder location
4. The shared folder syncs to your chosen local path
5. Create the film project inside the synced folder

**Caveats:**

- Free tier has transfer quotas (~5 GB/day depending on account age). For heavy video production, a paid plan (Pro I: 2 TB, ~$10/month) removes this.
- MEGA's sync client can be slower than Drive/OneDrive for many small files.
- E2E encryption means MEGA cannot help if you lose your password/recovery key. Save it.

**Sync speed:** Good. ~30-80 Mbps typical. The Pro plan removes speed throttling.

---

### Dropbox

**Best for:** Reliability above all else. Block-level sync (only uploads changed parts of files — great for large videos). Rock-solid conflict handling.

**Setup:**

1. Install [Dropbox](https://www.dropbox.com/install)
2. Create a folder → Share → add team emails with "Can edit"
3. The folder appears locally at:
   - **Windows:** `C:\Users\You\Dropbox\[folder]`
   - **macOS:** `/Users/You/Dropbox/[folder]`
4. Create the film project inside this folder
5. Right-click → **"Make available offline"** for the project folder

**Caveats:**

- Free tier is only 2 GB. Teams need Plus (2 TB, $10/month) or a team plan.
- Dropbox's block-level sync (delta sync) means if you re-render a 500 MB video with minor changes, it only uploads the changed blocks — much faster than other services.
- Best-in-class LAN sync: if two team members are on the same network, files transfer locally instead of via cloud.

**Sync speed:** Fastest for large files (delta sync). LAN sync for local teams is near-instant.

---

### Syncthing (No Cloud — Peer-to-Peer)

**Best for:** Privacy-maximal teams, local teams on same network, zero ongoing cost. No third-party server holds your data.

**Setup:**

1. Install [Syncthing](https://syncthing.net/) on every team member's machine
2. One person creates the project folder and shares it via Syncthing (generates a device ID)
3. Other team members add the device ID and accept the folder share
4. Files sync directly between computers — no cloud middleman
5. For remote teams: files sync whenever both machines are online. For always-on sync, one person can run Syncthing on a NAS or VPS as a relay.

**Caveats:**

- Both machines must be online at the same time for sync (or use a relay device).
- Initial sync of large projects can be slow over residential upload speeds.
- No web interface for browsing files — it's sync only. Use git for browsing text, cloud for binary sync.
- Technical setup: slightly more involved than cloud services. Worth it for the privacy and zero cost.

**Sync speed:** Limited by the slower of the two internet connections. On LAN: near-instant (100+ MB/s).

---

### NAS — Network Attached Storage (Local Server)

**Best for:** Teams in the same physical location (office, studio, home). Maximum speed. Maximum storage. Maximum privacy. One-time hardware cost, zero subscription. No internet needed.

**What it is:** A dedicated storage device plugged into your local network — essentially a private cloud server in your building. Every team member connects to it over the local network (1 Gbps or 10 Gbps Ethernet, or WiFi 6). Files transfer at hard-drive speed, not internet speed. A 5 GB render copies in seconds.

**Hardware options:**
| Device | Capacity | Price | Best For |
|--------|----------|-------|----------|
| **Synology DS224+** | 2-bay, up to 40 TB | ~$300 + drives | 2-4 person team |
| **Synology DS923+** | 4-bay, up to 80 TB | ~$600 + drives | 4-8 person team, 10 GbE option |
| **QNAP TS-464** | 4-bay, up to 80 TB | ~$550 + drives | HDMI out for direct monitor |
| **DIY TrueNAS** | Any old PC + drives | ~$200 + drives | Budget, technical users |
| **WD My Cloud EX2** | 2-bay, up to 40 TB | ~$250 + drives | Simplest setup, no IT skills needed |

**Setup:**

1. Buy a NAS, install drives (2× 8 TB WD Red or Seagate IronWolf is a good start for ~$400 total)
2. Connect NAS to your router via Ethernet
3. Follow the NAS setup wizard (Synology DSM, QNAP QTS) — takes 15 minutes
4. Create a shared folder called `film-projects` — set permissions so all team members can read/write
5. On each team member's computer, map the NAS as a network drive:
   - **Windows:** File Explorer → This PC → Map network drive → `\\nas-ip\film-projects` → assign drive letter (e.g., `N:`)
   - **macOS:** Finder → Go → Connect to Server → `smb://nas-ip/film-projects`
6. Create the film project inside the mapped drive (e.g., `N:\film-project\`)

**How team members access it:**

```
Every team member sees: N:\film-project\ (Windows) or /Volumes/film-projects/ (macOS)
It behaves exactly like a local folder. Save renders. Open renders. No sync client. No cloud.
```

**NAS + git together:**
The NAS holds the project. Git repo lives inside it. Team members work directly on the NAS share:

```bash
cd N:\film-project
git pull    # Pull latest text changes
# Work on renders — save to N:\film-project\renders\
# Files are instantly available to everyone (same drive)
git add . && git commit -m "[B] shot-04 take-02 selected" && git push
```

**NAS + remote team members (hybrid):**
If one team member works remotely, they can still connect:

- **VPN:** Connect to the office network via WireGuard or Tailscale → map the NAS drive → work as if local. Speed limited by internet connection.
- **Synology Drive / QNAP Qsync:** NAS vendor app that syncs a local folder to the NAS. Like Dropbox but the server is yours. Remote member gets a local copy synced automatically.

**Caveats:**

- Local only (unless VPN/remote access configured). Remote members need setup.
- One-time hardware cost ($500-1500 with drives). No subscription.
- Someone needs to manage it (updates, drive health, backups). Synology/QNAP make this easy — they send email alerts for drive failures.
- WiFi can bottleneck large transfers. Ethernet recommended for the main editing machine. WiFi 6 (802.11ax) handles 4K video fine.

**Sync speed:** Gigabit Ethernet: 110 MB/s. 10 GbE: 1,100 MB/s. A 5 GB render copies in ~45 seconds on 1 GbE, ~5 seconds on 10 GbE. The fastest option by far.

**NAS + cloud backup (belt and suspenders):**
For disaster recovery, configure the NAS to back up to a cloud service nightly:

- Synology Hyper Backup → Backblaze B2 ($6/TB/month) or Google Drive
- QNAP Hybrid Backup Sync → Backblaze B2 or OneDrive
- This gives you local speed + cloud safety. If the NAS dies, your renders are in the cloud.

| Service          | Free Storage               | Best For                   | Speed         | Privacy       | LAN Sync     | Delta Sync |
| ---------------- | -------------------------- | -------------------------- | ------------- | ------------- | ------------ | ---------- |
| **Google Drive** | 15 GB                      | Google Workspace teams     | Good          | Standard      | No           | No         |
| **OneDrive**     | 5 GB free / 1 TB with M365 | Windows teams, M365 orgs   | Excellent     | Standard      | No           | No         |
| **MEGA**         | 20 GB                      | Privacy-focused, budget    | Good          | E2E encrypted | No           | No         |
| **Dropbox**      | 2 GB / 2 TB paid           | Reliability, large files   | Best (delta)  | Standard      | Yes          | Yes        |
| **Syncthing**    | Unlimited (your disk)      | Privacy, local teams, free | Variable      | Full (P2P)    | Yes (native) | Yes        |
| **NAS**          | Unlimited (your drives)    | Local teams, max speed     | Fastest (LAN) | Full (local)  | Yes (native) | No         |

### Recommendation by Team Type

| Team Type                          | Recommended Service                                                                 |
| ---------------------------------- | ----------------------------------------------------------------------------------- |
| 2-3 friends, free budget           | **MEGA** (20 GB free) or **Syncthing** (free, unlimited)                            |
| Windows users on Microsoft 365     | **OneDrive** (1 TB included, seamless)                                              |
| Remote team, need reliability      | **Dropbox** (delta sync, rock-solid)                                                |
| Google Workspace org               | **Google Drive** (already paying for it)                                            |
| Privacy above all                  | **Syncthing** (no third party)                                                      |
| Local team, same network           | **Syncthing** LAN sync (instant, free) or **NAS** (fastest, no internet)            |
| Local team, serious production     | **NAS** (10 GbE, unlimited storage, one-time cost)                                  |
| Hybrid: local team + remote member | **NAS + Tailscale VPN** (local speed for office, remote access for distant members) |
| NAS + cloud backup                 | **NAS** for daily work + **Backblaze B2** nightly backup (speed + safety)           |

---

### Cloud Sync Troubleshooting

**"My teammate uploaded a render but I don't see it"**

1. Check cloud sync client is running (look for the tray icon)
2. Check the file isn't still uploading (look for sync status icon)
3. If using "Files On-Demand" or "Stream files", the file may exist but not be downloaded — right-click → "Always keep on this device"

**"Cloud sync is using all my disk space"**
Videos are large. Use selective sync to only sync the `renders/` and `audio/` folders, or set your cloud client to stream files on-demand and only download what you need.

**"I have a different cloud path than the team"**
The project structure is relative. As long as the folder CONTENTS are synced (renders/, audio/, canon/), the absolute path doesn't matter. Git handles paths within the repo; cloud handles the folder contents.

**"Two people's cloud sync clients are fighting over the same file"**
With role enforcement, this should never happen — only one person writes to `renders/` (Role B), only one to `audio/` (Role D). If it does happen, the last write wins. Cloud services handle this with "conflicted copy" files — check for `filename (conflicted copy).mp4` and coordinate with the other person.

**"My cloud sync is too slow for video files"**

- Compress renders before uploading (use H.265/HEVC instead of uncompressed)
- Use Dropbox (delta sync — only changed blocks upload on re-renders)
- For local teams, use Syncthing LAN sync (bypasses internet entirely)
- Split large renders: upload overnight, work on other shots during the day

---

## The Task Board (`tasks.md`)

A simple markdown file. No Jira, no Trello, no headache. One file everyone can see and edit.

```markdown
# Tasks

## TODO

- [ ] [A] Generate antagonist side-profile reference
- [ ] [B] Shot-04: write prompt, generate 3 takes
- [ ] [C] Assemble rough cut v1
- [ ] [D] Record protagonist voiceover lines 1-5

## IN PROGRESS

- [ ] [B] Shot-03: generating takes (3/5 done) — @personname

## DONE

- [x] [A] Protagonist front + 3/4 portraits generated
- [x] [B] Shot-01 prompt written and reviewed
```

**Convention:**

- `[ROLE]` tag on every task — everyone knows who owns it
- `@personname` on in-progress items — everyone knows who's working
- **The Lead owns `tasks.md`.** Only the Lead edits the task board to avoid merge conflicts. Team members communicate new tasks or status changes to the Lead (in chat), and the Lead updates `tasks.md` in the next commit. For rapid iteration, the Lead can designate a "task scribe" from the team.

---

## Troubleshooting

### "My skill says I'm not assigned a role"

Your `git config user.name` doesn't match any `@username` in the `README.md` team roster. Run `git config user.name` to see your current name, then compare with README. If your name is empty, set it: `git config user.name "your-username"`. If it doesn't match, either the Lead used the wrong username, or you need to set your name to match. Contact the Lead. Do not make changes until you're assigned.

### "git config user.name returns nothing"

You haven't set a git username. Set it to match what the Lead will put (or has put) in README: `git config user.name "your-username"`. This is mandatory — the skill uses it to identify you.

### "The skill is refusing to let me edit a file"

You're touching a file outside your role's ownership. Check the Role Detection table. Only the Lead can touch everything. If you genuinely need to cross roles, ask the Lead to reassign you.

### "I'm the Lead but the skill says someone else is"

Check `README.md`. The Lead entry must have your `@username` from `git config user.name`. If someone else is listed as Lead, they created the project — you need to coordinate.

### "Two people claim the same role"

Only the Lead can assign roles. The Lead edits `README.md`, commits, pushes. Whoever is in `README.md` wins. If you're both assigned the same role, the Lead made a mistake — tell them.

### "I pulled and my renders disappeared"

Renders are gitignored. They live in cloud storage, not git. Sync your cloud folder.

### "We edited the same shot file and git won't merge"

Stash, pull, pop. Keep both versions. Decide together which to use. This is why roles exist — Role B owns `shots/`, no one else edits them.

### "I need a reference image that doesn't exist yet"

Tell Role A. Add it as a TODO in `tasks.md`. Work on other shots while you wait.

### "My video take doesn't match the canon character"

Pull the latest canon. Regenerate. The canon is the single source of truth — if your output doesn't match it, your output is wrong.

### "We have different versions of the same file and we're confused"

Look at `git log --oneline` to see who changed what and when. The latest push wins unless the team decides otherwise.

---

## Team Size Recommendations

| Team Size     | Recommended Split                                                                                                                                                                                                                         |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1 person**  | You ARE all four roles. The structure still helps you stay organized.                                                                                                                                                                     |
| **2 people**  | Person 1: Roles A + C (stills + assembly). Person 2: Roles B + D (video + audio).                                                                                                                                                         |
| **3 people**  | Person 1: Role A (stills). Person 2: Role B (video). Person 3: Roles C + D (assembly + audio).                                                                                                                                            |
| **4 people**  | One role per person. Ideal. Everyone has clear ownership.                                                                                                                                                                                 |
| **5+ people** | Split Role B (video) across multiple people. Create subdirectories: `shots/b1/` for Person B1 (shots 1-5), `shots/b2/` for Person B2 (shots 6-10). Each sub-owner only touches their directory. Canon stays shared and read-only for all. |

---

## Cross-Skill Handoff

| When the team needs to...                  | Use this skill                                                  |
| ------------------------------------------ | --------------------------------------------------------------- |
| Write action prompts for each shot         | `dpf-continue-action-film` (60 categories, model grammar)       |
| Plan the full film structure and direction | `dpf-film-director` (8-layer framework, shot planning)          |
| Build the film concept and premise         | `dpf-ai-short-director` (STAMP, premise document, canon)        |
| Score the film before assembly             | `dpf-film-critic-scorer` (dimension scoring, improvement notes) |
| Generate video via CLI                     | `ai-video-generation` (inference.sh, 40+ models)                |
| Write Hailuo-specific prompts              | `hailuo-prompting` (camera commands, subject-reference)         |
| Write Kling-specific prompts               | `kling-prompting` (multi-shot, omni model)                      |
| Structure Seedance prompts                 | `seedance-prompt-structure` (element tags, style prefix)        |
| Edit and assemble in Premiere              | `dpf-senior-editor`                                             |
| Composite and VFX in After Effects         | `dpf-senior-motion-designer`                                    |
| Audio post-production                      | `audio-pro`                                                     |
| Design title sequence                      | `dpf-title-seq-master`                                          |

---

## Quick Start Checklist

### Lead (One Person Does This)

- [ ] Create the repo: `git init`, scaffold folders, `.gitignore`
- [ ] Write `README.md` using the exact template (premise, team roster, model, phases)
- [ ] Push to remote, share the clone URL
- [ ] Confirm each team member's `git config user.name` matches their `@username` in README
- [ ] Assign cloud sync folder and share link

### Team Members (Everyone Else)

- [ ] Get the clone URL from the Lead
- [ ] `git clone <url>`
- [ ] Set up cloud sync for `renders/` and `audio/`
- [ ] Verify: `git config user.name` matches your `@username` in README
- [ ] Run `git pull` — the skill auto-detects your role
- [ ] Work only in your role's directories

### All Team Members After Setup

- [ ] Pull before every session: `git pull`
- [ ] Work in your assigned directories only
- [ ] Track tasks in `tasks.md`
- [ ] Commit with `[ROLE]` tag at end of every session
- [ ] Push: `git push`

---

## Golden Rules

- **Only the Lead creates the repo.** One source of truth. One person starts it.
- **README.md is the constitution.** Roles, premise, status, team — all in one file. The skill reads it to know who you are.
- **Your role is enforced by the skill.** If the skill says you can't touch a file, you can't. This prevents conflicts before they happen.
- **Canon is sacred.** Everyone works from the same reference images. No exceptions.
- **One owner per file.** No two people edit the same shot file, task file, or canon file simultaneously. The skill enforces this through role ownership.
- **Push prompts, sync renders.** Text goes to git. Video goes to cloud. Never the reverse.
- **Commit every session.** `git add . && git commit -m "[ROLE] what you did" && git push`. Three commands. No excuses.
- **Pull before you start.** Every. Single. Time. Also re-reads README.md for role changes.
- **Tasks.md is the truth.** If it's not on the task board, it's not being worked on.
- **When stuck, ask the Lead.** Don't guess role changes. Don't touch another role's files. The Lead resolves conflicts.

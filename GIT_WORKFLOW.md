# Git Workflow Manual – Majesty_iFAS

## Overview
This guide explains how to keep all devices synchronized using Git with the GitHub repository: `https://github.com/hoferjo/Majesty_iFAS`

---

## 1. Initial Setup (First Time on a Device)

### Step 1: Clone the Repository
```powershell
cd C:\Users\<YourUsername>\Projects
git clone https://github.com/hoferjo/Majesty_iFAS.git
cd Majesty_iFAS
```

### Step 2: Verify the Clone
```powershell
git status
git log --oneline -n 3
```

You should see the latest commits without errors.

### Step 3: Set Your Git Identity (First Time Only)
```powershell
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

**Tip:** To set globally (all projects on this device):
```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Step 4: Create Virtual Environment (if needed)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 2. Daily Workflow

### Before Starting Work: Pull Latest Changes
Always pull before you start coding to avoid conflicts.

```powershell
git pull origin master
```

**What it does:**
- Fetches latest changes from GitHub
- Merges them into your local master branch
- Updates your working files

### After Making Changes: Commit and Push

#### Step 1: Check What Changed
```powershell
git status
```

Shows modified and new files.

#### Step 2: Stage Your Changes
```powershell
# Stage specific file
git add etl/transform.py

# Stage all changes
git add .
```

#### Step 3: View Changes Before Committing (Optional)
```powershell
git diff --staged
```

#### Step 4: Commit with Meaningful Message
```powershell
git commit -m "Add article sorting schema for DIN normteile"
```

**Good commit message format:**
- Start with a verb: "Add", "Fix", "Update", "Remove", "Refactor"
- Be specific: What changed and why
- Keep it under 72 characters for the headline

**Examples:**
```
git commit -m "Add three-level article sorting hierarchy"
git commit -m "Fix getArticleGroup() to return hauptgruppe, untergruppe, spezifikation"
git commit -m "Update article_list output format with sorting columns"
```

#### Step 5: Push to GitHub
```powershell
git push origin master
```

**What it does:**
- Uploads your commits to the remote repository (GitHub)
- Makes changes available to all other devices

---

## 3. Handling the `data/` Directory

**Important:** The `data/` directory is **ignored** by Git and should NOT be committed.

### What's Ignored
```
data/          # Local working data (not tracked)
.venv/         # Virtual environment (not tracked)
__pycache__/   # Python cache (not tracked)
*.pyc          # Compiled Python (not tracked)
```

### If You Accidentally Stage Data Files
```powershell
git reset HEAD data/
git checkout -- data/
```

This unstages the data files without deleting them locally.

---

## 4. Pulling Changes on Another Device

When you arrive at another device and want the latest code:

```powershell
cd c:\Users\<YourUsername>\Projects\Majesty_iFAS
git pull origin master
```

If you haven't cloned yet, see **Section 1: Initial Setup**.

---

## 5. Resolving Merge Conflicts

### If Pull Fails with Conflicts
```powershell
git pull origin master
# Error: CONFLICT in etl/transform.py
```

### Step 1: See Conflicted Files
```powershell
git status
```

### Step 2: Open and Resolve Conflicts
Open the conflicted file(s). Look for markers like:
```
<<<<<<< HEAD
your local version here
=======
remote version here
>>>>>>> origin/master
```

**Edit the file to keep the correct version**, then remove the markers.

### Step 3: Stage and Commit the Resolution
```powershell
git add etl/transform.py
git commit -m "Resolve merge conflict in etl/transform.py"
git push origin master
```

---

## 6. Checking History and Status

### View Recent Commits
```powershell
git log --oneline -n 10
```

Shows last 10 commits with short hashes and messages.

### View Full Commit Details
```powershell
git show <commit-hash>
```

Example:
```powershell
git show 073d6c0
```

### Check Current Branch
```powershell
git branch -v
```

Should show `* master 073d6c0 Ignore data/ directory and stop tracking generated data`

### View Remote Branches
```powershell
git branch -r
```

---

## 7. Useful One-Liners

### Sync with Latest Remote
```powershell
git fetch origin
git reset --hard origin/master
```

**Warning:** This overwrites your local changes. Use only if you want to discard local work.

### Undo Last Commit (Before Push)
```powershell
git reset --soft HEAD~1
```

Then edit and recommit.

### See What's Different from Remote
```powershell
git diff origin/master
```

### Stash Work (Save Temporarily)
```powershell
git stash
git pull origin master
git stash pop
```

Use this if you have uncommitted changes and want to pull.

---

## 8. Best Practices

✅ **DO:**
- Pull before starting work
- Commit frequently with clear messages
- Push at the end of each work session
- Test locally before pushing
- Keep commits focused on one task/feature

❌ **DON'T:**
- Commit large binary files (images, videos, data CSVs)
- Commit sensitive data (passwords, API keys)
- Force-push unless you know what you're doing
- Leave uncommitted changes at end of day
- Merge without testing

---

## 9. Team Workflow Example

**Person A (Laptop):**
```powershell
git pull origin master                    # Get latest
# ... edit config/article_sorting_schema.yaml ...
git add config/article_sorting_schema.yaml
git commit -m "Expand article sorting schema with new categories"
git push origin master
```

**Person B (Desktop):**
```powershell
git pull origin master                    # Gets Person A's changes
# ... sees the new schema in config/ ...
# Now both devices have the same version
```

---

## 10. Troubleshooting

### "fatal: 'origin' does not appear to be a git repository"
**Solution:** Your current folder is not a git repository. Navigate to the project root:
```powershell
cd c:\Users\jonas\Projects\Majesty_iFAS
```

### "error: Your local changes to the following files would be overwritten by merge"
**Solution:** Commit or stash your changes first:
```powershell
git stash              # Temporarily save changes
git pull origin master # Now pull
git stash pop          # Reapply your changes
```

### "nothing added to commit but untracked files present"
**Solution:** You created new files but didn't stage them:
```powershell
git add .
git commit -m "Add new configuration files"
git push origin master
```

### "Permission denied (publickey)"
**Solution:** SSH key issue. Use HTTPS instead or set up SSH keys:
```powershell
# Switch to HTTPS
git remote set-url origin https://github.com/hoferjo/Majesty_iFAS.git
```

---

## 11. Quick Cheat Sheet

| Task | Command |
|------|---------|
| Clone repo | `git clone https://github.com/hoferjo/Majesty_iFAS.git` |
| Get latest | `git pull origin master` |
| Check status | `git status` |
| Stage all | `git add .` |
| Commit | `git commit -m "message"` |
| Push | `git push origin master` |
| View history | `git log --oneline -n 10` |
| Undo last commit | `git reset --soft HEAD~1` |
| Stash work | `git stash` |
| List branches | `git branch -v` |

---

## 12. Getting Help

### Git Documentation
```powershell
git help <command>
```

Example: `git help pull`

### GitHub Support
Visit: https://docs.github.com/en/pull-requests

### Project Repository
https://github.com/hoferjo/Majesty_iFAS

---

## Notes

- **Current Status:** Repository is clean (~2.14 MiB), without large data files
- **Latest Commit:** `073d6c0` – "Ignore data/ directory and stop tracking generated data"
- **Branch:** `master` (main development branch)
- **Default Mode:** HTTPS (via `https://github.com/hoferjo/Majesty_iFAS.git`)

---

**Last Updated:** May 1, 2026

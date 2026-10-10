# Publish MForce with GitHub Desktop (no Git commands)

## Before publishing

1. Extract the ZIP so there is **one folder named `MForce`** containing `README.md`, `mforce`, `tests`, `data`, and `.github`. Do not upload the ZIP itself as the repository's main content.
2. Put the entire folder in the OneDrive location you want (example `D:\Gourishwar-personal\MForce`; if your actual OneDrive root differs, choose your real folder). Keep the source files together. Windows **Extract All** may create `MForce\MForce`; if so, choose the **inner folder** that contains `README.md`.
3. Double-click `TEST_MFORCE.bat`. If Python is unavailable, install Python 3.11+ and rerun it. You should see passing tests and a generated demo CSV. `output/` is automatically excluded from Git commits.

## GitHub Desktop steps

1. Download/open [GitHub Desktop](https://desktop.github.com/) and sign in.
2. In the menu choose **File → Add local repository → Choose** and select the `MForce` folder, not an individual `.py` file.
3. Since a ZIP folder does not contain `.git` history, Desktop may say **This directory does not appear to be a Git repository**. Choose **Create a repository here**. Check that its location is the *existing MForce folder* (not `MForce\MForce`).
4. Inspect **Changes**, enter a commit summary such as `Initial MForce simulation with tests`, and choose **Commit to main** (the button might show the current branch name).
5. Select **Publish repository**. Set name to **MForce**, write a description such as `Vehicle safety automation simulator with a tested fail-safe state machine`, and decide whether it should be public.
6. Open **View on GitHub** to verify `README.md`, `mforce/`, `data/scenarios/`, `tests/`, `docs/`, and `.github/workflows/tests.yml` are present.
7. Open your GitHub repository's **Actions** tab and review the test workflow. A green check means CI tests passed on GitHub; it does not certify real-vehicle safety.

Read [GitHub's official guide](https://docs.github.com/en/desktop/overview/creating-your-first-repository-using-github-desktop) for variations in UI labels.

## Important mistakes to avoid

- Do not drag an enclosing parent folder containing unrelated projects; use **one repository per project**.
- Do not upload `.venv/`, passwords, API keys, `.env` files, output logs, real user datasets, or machine-specific binaries.
- Do not create a blank GitHub repository and then upload only `main.py` in the browser — use GitHub Desktop so the folder structure is preserved.
- Avoid simultaneous Git edits/sync conflicts from two computers using the same OneDrive copy. Wait for sync before committing, or move your working repository outside an actively synchronized OneDrive directory.
- If GitHub prompts about large files, inspect them before committing. This template intentionally has no large datasets or models.
- To update: edit files, rerun `TEST_MFORCE.bat`, then **Commit** and **Push origin** in GitHub Desktop.

**Limitation:** You must click Publish in your own GitHub account. The ZIP itself does not create an online repository.

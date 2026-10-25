# Python automation

Tester Contact List application:

1. Register a new user, add a contact and check all details.
2. Submit an invalid birthdate and check the error and absence of a saved contact.
3. Delete a contact and check that it stays deleted after refresh.

## Run

Use Python 3.10 or newer. Open a terminal in this folder.

```bash
python -m venv .venv
```

Activate it on Windows Command Prompt:

```bat
.venv\\Scripts\\activate.bat
```

Or on macOS/Linux:

```bash
source .venv/bin/activate
```

Install and run:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m pytest -v --headed
```

On Linux, missing system libraries can be installed with `python -m playwright install --with-deps chromium`.

To run only the invalid-date test:

```bash
python -m pytest -v --headed -k invalid\_birthdate
```

## 


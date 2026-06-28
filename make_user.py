"""
make_user.py  -  generate a password hash for OTLAB_USERS.

    python3 make_user.py sumit
    (enter password when prompted)

Prints a JSON fragment you can paste/merge into the OTLAB_USERS env var.
"""

import getpass
import json
import sys

from werkzeug.security import generate_password_hash

if len(sys.argv) != 2:
    print("usage: python3 make_user.py <username>")
    sys.exit(1)

user = sys.argv[1]
pw = getpass.getpass(f"password for {user}: ")
if not pw:
    print("empty password, aborting")
    sys.exit(1)

print("\nAdd this user to OTLAB_USERS (merge with any existing users):")
print(json.dumps({user: generate_password_hash(pw)}))

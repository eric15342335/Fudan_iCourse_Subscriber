#!/usr/bin/env python3
"""Log in to iCourse once (scan the QR code) and save the session for later runs.

    python -m scripts.icourse_login

Run this before starting several ``run_lectures`` processes at once, so they reuse
the saved session instead of asking for one QR scan each.
"""

from scripts.lecture_batch import login

if __name__ == "__main__":
    login()
    print("Session saved; run_lectures will reuse it.")

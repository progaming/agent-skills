#!/usr/bin/env python3
import json, os, re, subprocess, base64, argparse, shutil
from datetime import datetime

# Allow importing score_applicants from the same directory
import sys
sys.path.insert(0, os.path.dirname(__file__))

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from score_applicants import (
    score_applicants, print_results, default_workspace,
    extract_body_text, find_attachments
)


def strip_ansi_and_log(s):
    s = re.sub(r"\x1b\[[0-9;]*m", "", s)
    lines = s.splitlines()
    out = []
    for line in lines:
        if line.startswith("Using keyring backend:"):
            continue
        out.append(line)
    return "\n".join(out)


def gws_json(cmd_args):
    # Run gws directly (no PowerShell wrapper) to avoid quoting issues.
    gws_exe = shutil.which("gws")
    if gws_exe:
        result = subprocess.run([gws_exe] + cmd_args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    else:
        result = subprocess.run(["gws"] + cmd_args, capture_output=True, text=True, shell=True)
    output = strip_ansi_and_log(result.stdout)
    # Try entire output as single JSON first (handles pretty-printed responses).
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        pass
    lines = output.splitlines()
    data = None
    for line in lines:
        line = line.strip()
        if not line or line[0] not in "{[":
            continue
        try:
            page = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data is None:
            data = page
        else:
            for key in page:
                if key in data and isinstance(data[key], list) and isinstance(page[key], list):
                    data[key].extend(page[key])
                else:
                    data[key] = page[key]
    return data or {}


def fetch_message_ids(after_date):
    params = json.dumps({"userId": "me", "q": f"in:inbox to:hr@progaming.co.th after:{after_date}"})
    return gws_json(["gmail", "users", "messages", "list", "--params", params, "--page-all", "--format", "json"]).get("messages", [])


def fetch_message(msg_id):
    params = json.dumps({"userId": "me", "id": msg_id, "format": "full"})
    return gws_json(["gmail", "users", "messages", "get", "--params", params, "--format", "json"])


def download_attachment(msg_id, attach_id):
    params = json.dumps({"userId": "me", "messageId": msg_id, "id": attach_id})
    data = gws_json(["gmail", "users", "messages", "attachments", "get", "--params", params, "--format", "json"])
    if data.get("data"):
        b64 = data["data"].replace("-", "+").replace("_", "/")
        padding = 4 - len(b64) % 4
        if padding != 4:
            b64 += "=" * padding
        return base64.b64decode(b64)
    return None


def extract_headers(msg):
    headers = {}
    for h in msg.get("payload", {}).get("headers", []):
        headers[h["name"].lower()] = h["value"]
    return headers


def main():
    parser = argparse.ArgumentParser(description="Fetch and score ProGaming applicants from Gmail.")
    parser.add_argument("--after", default=datetime.now().strftime("%Y/%m/%d"),
                        help="Search emails after this date (default: today)")
    parser.add_argument("--workspace", help="Output workspace directory (default: auto-create dated dir)")
    args = parser.parse_args()

    workspace = args.workspace or default_workspace()
    full_dir = os.path.join(workspace, "applicant_full")
    attach_dir = os.path.join(workspace, "applicant_attachments")
    os.makedirs(full_dir, exist_ok=True)
    os.makedirs(attach_dir, exist_ok=True)

    print(f"Searching Gmail for applicants after {args.after}...")
    messages = fetch_message_ids(args.after)
    print(f"Found {len(messages)} messages")

    meta_list = []

    for i, msg_ref in enumerate(messages):
        msg_id = msg_ref["id"]
        print(f"Fetching message {i+1}/{len(messages)}: {msg_id}")
        msg_data = fetch_message(msg_id)

        with open(os.path.join(full_dir, f"{msg_id}.json"), "w", encoding="utf-8") as f:
            json.dump(msg_data, f, ensure_ascii=False, indent=2)

        headers = extract_headers(msg_data)
        subject = headers.get("subject", "")
        from_addr = headers.get("from", "")
        snippet = msg_data.get("snippet", "")

        meta_list.append({"id": msg_id, "subject": subject, "from": from_addr, "snippet": snippet})

        for att in find_attachments(msg_data):
            data = download_attachment(msg_id, att["attachmentId"])
            if data:
                with open(os.path.join(attach_dir, f"{msg_id}_{att['filename']}"), "wb") as f:
                    f.write(data)
                print(f"  Downloaded: {att['filename']}")

    with open(os.path.join(workspace, "applicant_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta_list, f, ensure_ascii=False, indent=2)

    print(f"\nScoring applicants...")
    results, summary = score_applicants(workspace, verbose=True)
    out_csv = os.path.join(workspace, "applicants_results.csv")
    print_results(results, summary, out_csv=out_csv)


if __name__ == "__main__":
    main()

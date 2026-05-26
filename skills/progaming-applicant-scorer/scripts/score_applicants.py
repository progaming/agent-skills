import json, os, re, argparse, base64, sys
import pdfplumber

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

TIER_1 = ["จุฬาลงกรณ์", "chulalongkorn", "มหิดล", "mahidol", "เกษตรศาสตร์", "kasetsart",
          "ธรรมศาสตร์", "thammasat", "เชียงใหม่", "chiang mai", "cmu",
          "ลาดกระบัง", "kmitl", "บางมด", "kmutt", "นอร์ทบางกอก", "kmutnb",
          "ศิลปากร", "silpakorn", "สงขลานครินทร์", "prince of songkla", "psu"]
TIER_2 = ["นเรศวร", "naresuan", "ขอนแก่น", "khon kaen", "บูรพา", "burapha",
          "ศรีนครินทรวิโรฒ", "srinakharinwirot", "อุบลราชธานี", "ubon ratchathani",
          "สุรนารี", "suranaree", "วลัยลักษณ์", "walailak", "แม่ฟ้าหลวง", "mae fah luang"]
TIER_3 = ["ราชภัฏ", "rajabhat", "ราชมงคล", "rajamangala", "เทคโนโลยีราชมงคล", "rmut"]

FULLSTACK_JD = {
    "frontend": ["react", "typescript", "html5", "css3", "html", "css", "frontend", "front-end", "angular", "vue"],
    "backend": ["node.js", "nodejs", "restful", "rest api", "api design", "backend", "back-end", "express", "nestjs"],
    "general": ["web application", "dashboard", "visualization", "interactive", "fullstack", "full stack", "full-stack", "web dev"]
}

SYSTEM_ANALYST_JD = {
    "analysis": ["requirement gathering", "gather requirement", "business analysis", "system analysis", "analyze requirement", "วิเคราะห์", "รวบรวมความต้องการ", "requirement"],
    "documentation": ["system specification", "data flow diagram", "dfd", "use case", "usecase", "เอกสาร", "documentation", "specification", "spec"],
    "technical_comm": ["restful api", "database", "web application", "communicate", "coordinator", "ประสานงาน", "สื่อสาร"],
    "trends": ["ai", "automation", "gamification", "machine learning", "artificial intelligence"]
}


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def extract_body_text(msg_data):
    body_text = ""
    def walk_parts(parts):
        nonlocal body_text
        for part in parts:
            mime = part.get("mimeType", "")
            body = part.get("body", {})
            if mime == "text/plain" and body.get("data"):
                try:
                    decoded = base64.urlsafe_b64decode(body["data"]).decode("utf-8", errors="replace")
                    body_text += decoded + "\n"
                except:
                    pass
            elif mime == "text/html" and not body_text and body.get("data"):
                try:
                    decoded = base64.urlsafe_b64decode(body["data"]).decode("utf-8", errors="replace")
                    text = re.sub(r"<[^>]+>", " ", decoded)
                    text = re.sub(r"\s+", " ", text)
                    body_text += text + "\n"
                except:
                    pass
            if "parts" in part:
                walk_parts(part["parts"])
    payload = msg_data.get("payload", {})
    if "parts" in payload:
        walk_parts(payload["parts"])
    else:
        body = payload.get("body", {})
        if body.get("data"):
            try:
                body_text = base64.urlsafe_b64decode(body["data"]).decode("utf-8", errors="replace")
            except:
                pass
    return body_text


def find_attachments(msg_data):
    # Return list of dicts: [{"filename": str, "attachmentId": str}, ...]
    attachments = []
    def walk_parts(parts):
        for part in parts:
            fn = part.get("filename", "")
            body = part.get("body", {})
            if fn.lower().endswith(".pdf") and body.get("attachmentId"):
                attachments.append({"filename": fn, "attachmentId": body["attachmentId"]})
            if "parts" in part:
                walk_parts(part["parts"])
    payload = msg_data.get("payload", {})
    if "parts" in payload:
        walk_parts(payload["parts"])
    return attachments


def extract_text_from_pdf(pdf_path):
    if not pdf_path or not os.path.exists(pdf_path):
        return ""
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def is_valid_applicant(subject, body, snippet, from_addr=""):
    text = (subject + body + snippet).lower()
    from_lower = from_addr.lower()
    
    app_keywords = ["สมัคร", "apply", "application", "สนใจ", "ส่งใบสมัคร", "resume", "cv"]
    if not any(k in text for k in app_keywords):
        return False
    
    progaming_keywords = ["progaming", "โปรเกมมิ่ง", "fullstack", "full stack", "developer", 
                          "system analyst", "analyst", "backend", "frontend", "web application"]
    if not any(k in text for k in progaming_keywords):
        return False
    
    # Exclude by sender domain (platform / marketing emails)
    exclude_domains = ["linkedin.com", "jobsdb.com", "seek.com", "uniqlo.com", 
                       "jobfinfin.com", "jobthai.com", "jobbkk.com", "thailand.uniqlo.com"]
    for domain in exclude_domains:
        if domain in from_lower:
            return False
    
    # Exclude obvious spam / marketing in body text
    exclude_body = ["weekly highlight", "สมัครงาน.com", "jobfinfin", "wom", "keds"]
    if any(k in text for k in exclude_body):
        return False
    
    return True


def get_university_score(text):
    text_lower = text.lower()
    for name in TIER_1:
        if name in text_lower:
            return 5, name
    for name in TIER_2:
        if name in text_lower:
            return 3, name
    for name in TIER_3:
        if name in text_lower:
            return 2, name
    uni_patterns = [
        r"มหาวิทยาลัย([^\s\n]{2,20})",
        r"university\s+of\s+([a-z\s]+)",
        r"([a-z]+)\s+university"
    ]
    for pat in uni_patterns:
        m = re.search(pat, text_lower)
        if m:
            return 2, m.group(0)
    return 3, "Unknown"


def get_field_score(text):
    text_lower = text.lower()
    tier1_fields = ["วิทยาการคอมพิวเตอร์", "computer science", "cs",
                    "วิศวกรรมซอฟต์แวร์", "software engineering", "se",
                    "เทคโนโลยีสารสนเทศ", "information technology", "it",
                    "วิศวกรรมคอมพิวเตอร์", "computer engineering"]
    for f in tier1_fields:
        if f in text_lower:
            return 5, f
    tier2_fields = ["สารสนเทศ", "information systems", "is",
                    "วิทยาศาสตร์ข้อมูล", "data science", "ds",
                    "เทคโนโลยีดิจิทัล", "digital technology"]
    for f in tier2_fields:
        if f in text_lower:
            return 4, f
    tier3_fields = ["คณิตศาสตร์", "mathematics", "math",
                    "สถิติ", "statistics", "stat",
                    "ฟิสิกส์", "physics",
                    "ธุรกิจ", "business", "ba",
                    "บริหาร", "management"]
    for f in tier3_fields:
        if f in text_lower:
            return 2, f
    return 3, "Unknown"


def get_salary_info(text):
    text_lower = text.lower()
    salary_sections = []
    patterns = [
        r"(?:เงินเดือน|salary|expected salary|ค่าจ้าง|salary expectation|expected income|preferred pay)[\s:=]*(.{0,30})",
        r"(?:expected remuneration|desired salary|preferred salary)[\s:=]*(.{0,30})",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text_lower):
            salary_sections.append(m.group(1))
    for m in re.finditer(r"(\d[\d,\.]{3,7})\s*(?:บาท|baht|thb|b\.)", text_lower):
        salary_sections.append(m.group(1))
    
    # k/K suffix matching (e.g. 25k -> 25000)
    for m in re.finditer(r"(\d{1,2})\s*[kK]\b", text_lower):
        val = int(m.group(1)) * 1000
        salary_sections.append(str(val))
    
    for section in salary_sections:
        numbers = re.findall(r"\d[\d,\.]+", section)
        for num_str in numbers:
            val = num_str.replace(",", "").replace(".", "")
            try:
                num = int(val)
                if 10000 <= num <= 100000:
                    if num < 25000:
                        return num, 5
                    elif num < 35000:
                        return num, 4
                    elif num < 45000:
                        return num, 3
                    elif num < 60000:
                        return num, 2
                    else:
                        return num, 1
            except:
                pass
    return None, 3


def get_employment_status(text):
    # Return only Fresh Graduate or Unknown.
    text_lower = text.lower()
    if any(k in text_lower for k in ["จบใหม่", "fresh graduate", "new graduate", "recent graduate", "graduated in", "สำเร็จการศึกษา", "เพิ่งจบ", "จบปี", "graduate in 202"]):
        return "Fresh Graduate"
    return "Unknown"


def get_jd_fit_score(text, position):
    text_lower = text.lower()
    
    if position == "Fullstack Developer":
        frontend_hits = sum(1 for k in FULLSTACK_JD["frontend"] if k in text_lower)
        backend_hits = sum(1 for k in FULLSTACK_JD["backend"] if k in text_lower)
        general_hits = sum(1 for k in FULLSTACK_JD["general"] if k in text_lower)
        
        total_hits = min(frontend_hits + backend_hits + general_hits, 8)
        if total_hits >= 6:
            return 5, f"Strong ({total_hits})"
        elif total_hits >= 4:
            return 4, f"Good ({total_hits})"
        elif total_hits >= 2:
            return 3, f"Moderate ({total_hits})"
        elif total_hits >= 1:
            return 2, f"Weak ({total_hits})"
        else:
            return 3, "Unknown"
            
    elif position == "System Analyst":
        analysis_hits = sum(1 for k in SYSTEM_ANALYST_JD["analysis"] if k in text_lower)
        doc_hits = sum(1 for k in SYSTEM_ANALYST_JD["documentation"] if k in text_lower)
        comm_hits = sum(1 for k in SYSTEM_ANALYST_JD["technical_comm"] if k in text_lower)
        trend_hits = sum(1 for k in SYSTEM_ANALYST_JD["trends"] if k in text_lower)
        
        total_hits = min(analysis_hits + doc_hits + comm_hits + trend_hits, 8)
        if total_hits >= 6:
            return 5, f"Strong ({total_hits})"
        elif total_hits >= 4:
            return 4, f"Good ({total_hits})"
        elif total_hits >= 2:
            return 3, f"Moderate ({total_hits})"
        elif total_hits >= 1:
            return 2, f"Weak ({total_hits})"
        else:
            return 3, "Unknown"
    
    return 3, "Unknown"


# ---------------------------------------------------------------------------
# Main scoring pipeline
# ---------------------------------------------------------------------------

def score_applicants(workspace, verbose=True):
    # Score all applicants found in the given workspace directory.
    # Returns (results_list, summary_dict).
    META_PATH = os.path.join(workspace, "applicant_meta.json")
    FULL_DIR = os.path.join(workspace, "applicant_full")
    ATTACH_DIR = os.path.join(workspace, "applicant_attachments")

    if not os.path.exists(META_PATH):
        raise FileNotFoundError(f"Metadata not found: {META_PATH}")

    with open(META_PATH, "r", encoding="utf-8") as f:
        meta_list = json.load(f)

    results = []
    seen = set()

    for meta in meta_list:
        msg_id = meta["id"]
        msg_path = os.path.join(FULL_DIR, f"{msg_id}.json")
        if not os.path.exists(msg_path):
            continue

        with open(msg_path, "r", encoding="utf-8") as f:
            msg_data = json.load(f)

        body_text = extract_body_text(msg_data)
        subject = meta.get("subject", "")
        snippet = meta.get("snippet", "")
        from_addr = meta.get("from", "")

        if not is_valid_applicant(subject, body_text, snippet, from_addr):
            if verbose:
                print(f"Skipping: {subject or '(no subject)'} | from: {from_addr}")
            continue

        pdf_text = ""
        attachments = find_attachments(msg_data)
        for att in attachments:
            pdf_path = os.path.join(ATTACH_DIR, f"{msg_id}_{att['filename']}")
            pdf_text += extract_text_from_pdf(pdf_path) + "\n"

        combined_text = body_text + "\n" + pdf_text + "\n" + snippet

        position = "Unknown"
        if any(k in (subject + body_text).lower() for k in ["system analyst", "sa ", "analyst"]):
            position = "System Analyst"
        elif any(k in (subject + body_text).lower() for k in ["fullstack", "full stack", "full-stack", "backend", "frontend", "developer", "dev"]):
            position = "Fullstack Developer"

        # Clean name: strip quotes and whitespace
        name_match = re.search(r"^([^<]+)", from_addr)
        name = name_match.group(1).strip() if name_match else from_addr
        name = name.strip('"').strip("'").strip()

        dedup_key = (name.lower(), position)
        if dedup_key in seen:
            if verbose:
                print(f"Duplicate: {name}")
            continue
        seen.add(dedup_key)

        uni_score, uni_name = get_university_score(combined_text)
        field_score, field_name = get_field_score(combined_text)
        salary_val, salary_score = get_salary_info(combined_text)
        emp_status = get_employment_status(combined_text)
        jd_score, jd_note = get_jd_fit_score(combined_text, position)

        total = uni_score + field_score + salary_score + jd_score

        results.append({
            "rank": 0,
            "name": name,
            "position": position,
            "university": uni_name,
            "field": field_name,
            "salary": f"฿{salary_val:,}" if salary_val else "Not declared",
            "status": emp_status,
            "scores": f"{uni_score}/{field_score}/{salary_score}/{jd_score}",
            "total": total,
            "jd_fit": jd_note,
            "note": "Need follow-up on salary" if not salary_val else ""
        })

    results.sort(key=lambda x: (-x["total"], x["name"]))
    for i, r in enumerate(results):
        r["rank"] = i + 1

    summary = {
        "total": len(results),
        "with_salary": sum(1 for r in results if r["salary"] != "Not declared"),
        "fresh_graduates": sum(1 for r in results if r["status"] == "Fresh Graduate"),
        "fullstack": sum(1 for r in results if r["position"] == "Fullstack Developer"),
        "system_analyst": sum(1 for r in results if r["position"] == "System Analyst"),
    }
    return results, summary


def print_results(results, summary, out_csv=None):
    # Print Markdown table to stdout and optionally write CSV.
    print(f"\nTotal valid applicants: {summary['total']}")
    print(f"With salary declared: {summary['with_salary']}")
    print(f"Fresh Graduates: {summary['fresh_graduates']}")
    print(f"For Fullstack Developer: {summary['fullstack']}")
    print(f"For System Analyst: {summary['system_analyst']}")

    print()
    print("| Rank | Name | Position | University | Field | Salary | Status | Score (U/F/S/J) | Total | JD Fit | Note |")
    print("|------|------|----------|------------|-------|--------|--------|-----------------|-------|--------|------|")
    for r in results:
        print(f"| {r['rank']} | {r['name']} | {r['position']} | {r['university']} | {r['field']} | {r['salary']} | {r['status']} | {r['scores']} | {r['total']} | {r['jd_fit']} | {r['note']} |")

    if out_csv:
        import csv
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["rank", "name", "position", "university", "field", "salary", "status", "scores", "total", "jd_fit", "note"])
            writer.writeheader()
            writer.writerows(results)
        print(f"\nCSV saved to: {out_csv}")


def _find_project_root():
    """Walk up from the script location to find the project root (directory containing .agents/)."""
    d = os.path.abspath(os.path.dirname(__file__))
    while True:
        if os.path.isdir(os.path.join(d, ".agents")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    raise RuntimeError("Could not locate project root (no .agents/ directory found)")


def default_workspace():
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = _find_project_root()
    return os.path.join(root, "tmp", f"applicants_{ts}")

def main():
    parser = argparse.ArgumentParser(description="Score ProGaming applicants from local Gmail exports.")
    parser.add_argument("--workspace", help="Path to workspace directory (default: auto-create dated dir under Cowork/tmp)")
    args = parser.parse_args()

    workspace = args.workspace or default_workspace()
    os.makedirs(os.path.join(workspace, "applicant_full"), exist_ok=True)
    os.makedirs(os.path.join(workspace, "applicant_attachments"), exist_ok=True)

    results, summary = score_applicants(workspace, verbose=True)
    out_csv = os.path.join(workspace, "applicants_results.csv")
    print_results(results, summary, out_csv=out_csv)


if __name__ == "__main__":
    main()
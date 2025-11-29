# scripts/add_categories.py
import json
from pathlib import Path

FAQ_PATH = Path("data/faq.json")
if not FAQ_PATH.exists():
    print("data/faq.json not found — create it first.")
    raise SystemExit(1)

with FAQ_PATH.open("r", encoding="utf-8") as f:
    faqs = json.load(f)

def infer_category(tags):
    tags = [t.lower() for t in (tags or [])]
    if any(t in tags for t in ("sale", "sales", "pricing", "enterprise", "subscription", "trial")):
        return "sales"
    if any(t in tags for t in ("marketing", "campaign", "analytics", "leads", "email")):
        return "marketing"
    if any(t in tags for t in ("support", "account", "password", "troubleshooting", "onboarding", "crm", "integration", "technical")):
        return "support"
    if any(t in tags for t in ("billing", "refund", "payment", "invoice")):
        return "billing"
    if any(t in tags for t in ("technical", "offline", "network", "app")):
        return "technical"
    return "general"

changed = False
for it in faqs:
    if "category" not in it:
        it["category"] = infer_category(it.get("tags", []))
        changed = True

if changed:
    with FAQ_PATH.open("w", encoding="utf-8") as f:
        json.dump(faqs, f, indent=2, ensure_ascii=False)
    print("Wrote categories to data/faq.json")
else:
    print("No changes — categories already present")

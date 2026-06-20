"""Attach media (diagram/figure + curated video + sourced deep-dive notes) to topics.

Run with: python3 media/apply_media.py
Idempotent: writes a 'media' object onto each listed topic in content/*.json.
Edit MEDIA below to add/adjust; re-run to apply. Image paths are relative to the
project root so the bot resolves them with BASE / path.
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CONTENT = BASE / "content"

# topic_id -> media dict
MEDIA = {
    # ---- SPC ----
    "spc-02": {
        "image": "media/diagrams/empirical_rule.png",
        "image_caption": "The empirical rule: 68–95–99.7 under the normal curve",
        "video": {"title": "Std Deviation, Normal Distribution & the 68-95-99.7 Rule",
                  "url": "https://www.youtube.com/watch?v=rdmkSIpn6_U"},
        "web_notes": ("In a stable, normal process ~68% of output falls within ±1σ of the mean, "
                      "~95% within ±2σ, and ~99.7% within ±3σ. That is why ±3σ control limits raise "
                      "only ~1-in-370 false alarms — a point beyond them is almost always a real "
                      "special cause, not chance."),
        "sources": [
            {"title": "Empirical Rule — Statistics How To", "url": "https://www.statisticshowto.com/probability-and-statistics/statistics-definitions/empirical-rule/"},
            {"title": "Empirical Rule (68-95-99.7) — Built In", "url": "https://builtin.com/data-science/empirical-rule"},
        ],
    },
    "spc-03": {
        "image": "media/diagrams/spc_xbar_r.png",
        "image_caption": "X̄/R control chart — the red point is an out-of-control signal",
        "video": {"title": "Control Charts Made Simple: X-bar & R Basics",
                  "url": "https://www.youtube.com/watch?v=7xRQUEsU-Sw"},
        "web_notes": ("The X̄ chart tracks the subgroup average to watch process centering; the R chart "
                      "tracks within-subgroup range to watch spread. Read the R chart first — if spread "
                      "is unstable, the X̄ limits (which are computed from R̄) cannot be trusted."),
        "sources": [
            {"title": "X-bar R Control Charts — Six Sigma Study Guide", "url": "https://sixsigmastudyguide.com/x-bar-r-control-charts/"},
            {"title": "Xbar-R Charts Part 1 — SPC for Excel", "url": "https://www.spcforexcel.com/knowledge/variable-control-charts/xbar-r-charts-part-1/"},
        ],
    },
    "spc-04": {
        "image": "media/diagrams/spc_xbar_r.png",
        "image_caption": "An out-of-control signal: one point beyond the upper control limit",
        "video": {"title": "Control Charts Made Simple: X-bar & R Basics",
                  "url": "https://www.youtube.com/watch?v=7xRQUEsU-Sw"},
        "web_notes": ("Beyond points outside the limits, hunt for non-random patterns: a run of 7+ points "
                      "on one side of the centerline, steady trends, or points hugging the limits. These "
                      "Western Electric / Nelson rules catch a process shift before any single point ever "
                      "breaches a control limit."),
        "sources": [
            {"title": "Interpreting an X-bar / R Chart — Quality America", "url": "https://qualityamerica.com/LSS-Knowledge-Center/statisticalprocesscontrol/interpreting_an_x-bar___r_chart.php"},
            {"title": "X-bar R Control Charts — Six Sigma Study Guide", "url": "https://sixsigmastudyguide.com/x-bar-r-control-charts/"},
        ],
    },
    "spc-07": {
        "image": "media/diagrams/process_capability.png",
        "image_caption": "Cp vs Cpk — an off-center process drags Cpk below Cp",
        "video": {"title": "Process Capability: Cp, Cpk, Sigma Level (ASQ Fellow)",
                  "url": "https://www.youtube.com/watch?v=zJS4o2lkGak"},
        "web_notes": ("Cp compares the tolerance width to the process spread (6σ) and ignores centering; "
                      "Cpk also penalizes how far the mean sits from target. Cpk ≤ Cp always, and they are "
                      "equal only when the process is perfectly centered. A common automotive floor is "
                      "Cpk ≥ 1.33."),
        "sources": [
            {"title": "Process Capability Cp Cpk — Six Sigma Study Guide", "url": "https://sixsigmastudyguide.com/process-capability-cp-cpk/"},
            {"title": "Guide to Process Capability — 1factory", "url": "https://www.1factory.com/quality-academy/guide-process-capability.html"},
        ],
    },
    # ---- GD&T ----
    "gdt-04": {
        "image": "media/diagrams/gdt_position_frame.png",
        "image_caption": "Datums A→B→C form the datum reference frame in the control frame",
        "video": {"title": "GD&T: Understanding Datums",
                  "url": "https://www.youtube.com/watch?v=fUXMoz4va9g"},
        "web_notes": ("A datum reference frame locks the part's six degrees of freedom using primary, "
                      "secondary, and tertiary datums — the primary removes 3, the secondary 2, the tertiary 1. "
                      "Datum order matters: it sets how the part seats for inspection, so swapping A and B "
                      "changes the measured result."),
        "sources": [
            {"title": "The Datum Reference Frame — GD&T Basics", "url": "https://www.gdandtbasics.com/datum-reference-frame/"},
            {"title": "Datum Reference Frame Explained — FARO", "url": "https://www.faro.com/en/Resource-Library/Article/datum-reference-frame-in-gdt-an-explanation-with-figures"},
        ],
    },
    "gdt-07": {
        "image": "media/diagrams/gdt_position_frame.png",
        "image_caption": "Reading a position control frame: symbol | Ø tol + Ⓜ | datums",
        "video": {"title": "GD&T Feature Control Frame Basics",
                  "url": "https://www.youtube.com/watch?v=mA6RrNrRYUI"},
        "web_notes": ("Position with an Ⓜ (MMC) modifier grants bonus tolerance: as the feature departs "
                      "from its maximum-material size, the allowable position tolerance grows by the same "
                      "amount. This rewards parts with extra clearance and accepts more good parts than "
                      "fixed (RFS) position."),
        "sources": [
            {"title": "True Position — GD&T Basics", "url": "https://www.gdandtbasics.com/true-position/"},
            {"title": "Maximum Material Condition (MMC) — GD&T Basics", "url": "https://www.gdandtbasics.com/maximum-material-condition/"},
        ],
    },
    # ---- FMEA ----
    "fmea-04": {
        "image": "media/diagrams/fmea_risk_matrix.png",
        "image_caption": "Severity × Occurrence risk — Detection is the third axis of RPN",
        "video": {"title": "AIAG-VDA FMEA: Ranking Severity, Occurrence, Detection",
                  "url": "https://www.youtube.com/watch?v=eL6Qo00EFm0"},
        "web_notes": ("Severity rates how bad the effect is (a 1–10 that detection can never reduce), "
                      "Occurrence how often the cause happens, and Detection how likely current controls "
                      "catch it before escape. Severity falls only by changing the design; Detection falls "
                      "by improving controls."),
        "sources": [
            {"title": "FMEA S/O/D Rating Tables (1–10)", "url": "https://fmearatings.com/"},
            {"title": "Severity in FMEA (AIAG-VDA) — Quality Assist", "url": "https://quasist.com/fmea/severity-in-fmea/"},
        ],
    },
    "fmea-05": {
        "image": "media/diagrams/fmea_risk_matrix.png",
        "image_caption": "Action Priority weights Severity first, then Occurrence, then Detection",
        "video": {"title": "AIAG-VDA FMEA: Ranking Severity, Occurrence, Detection",
                  "url": "https://www.youtube.com/watch?v=eL6Qo00EFm0"},
        "web_notes": ("The AIAG-VDA handbook replaced the old RPN (S×O×D) with Action Priority (H/M/L) because "
                      "equal RPNs could hide very different risks. AP weights Severity first, then Occurrence, "
                      "then Detection — so a high-severity failure is prioritized even when it is rare and "
                      "easy to detect."),
        "sources": [
            {"title": "FMEA Action Priority (AP) — Relyence", "url": "https://relyence.com/help/user-guide/fmea-ap.html"},
            {"title": "Action Priority in FMEA — Quality Engineer Stuff", "url": "https://qualityengineerstuff.com/doc/action-priority-in-fmea/"},
        ],
    },
    # ---- APQP ----
    "apqp-01": {
        "image": "media/diagrams/apqp_phases.png",
        "image_caption": "The five phases of APQP, gated from planning to corrective action",
        "video": {"title": "APQP Explained: Advanced Product Quality Planning",
                  "url": "https://www.youtube.com/watch?v=HHwCNm8WM4Q"},
        "web_notes": ("APQP runs in five gated phases — Plan & Define, Product Design, Process Design, "
                      "Product & Process Validation, and Feedback/Corrective Action — each with required "
                      "deliverables. The core tools (DFMEA, PFMEA, Control Plan, MSA, SPC, PPAP) are produced "
                      "across these phases, not bolted on at the end."),
        "sources": [
            {"title": "5 Phases of APQP — Unichrone", "url": "https://unichrone.com/blog/quality-management/5-phases-of-advanced-product-quality-planning/"},
            {"title": "APQP — Quality-One", "url": "https://quality-one.com/apqp/"},
        ],
    },
    # ---- FMEA (figure from the FMEA Handbook) ----
    "fmea-03": {
        "image": "media/book_figures/fmea-handbook-p53-x1459.png",
        "image_caption": "FMEA 'focus element': analyze it with the levels above and below",
        "video": {"title": "AIAG-VDA FMEA: Ranking Severity, Occurrence, Detection",
                  "url": "https://www.youtube.com/watch?v=eL6Qo00EFm0"},
        "web_notes": ("Every failure mode sits in a chain: a Cause triggers the failure Mode, which produces "
                      "an Effect felt by the customer. The same problem is an 'effect' at one level and a "
                      "'cause' at the next — which is why FMEA analyzes the focus element together with the "
                      "level above and below it."),
        "sources": [
            {"title": "FMEA S/O/D Rating Tables (1–10)", "url": "https://fmearatings.com/"},
            {"title": "AIAG-VDA DFMEA Guide — Quality Engineer Stuff", "url": "https://qualityengineerstuff.com/aiag-vda-dfmea/"},
        ],
    },
    # ---- Physics / Materials (figures from Jacob's books) ----
    "phys-03": {
        "image": "media/book_figures/teach-yourself-electricity-and-electroni-p31-x1128.png",
        "image_caption": "Atomic structure — protons, neutrons, and the electrons that carry current",
        "web_notes": ("Current is the flow of electrons through a conductor, voltage is the pressure pushing "
                      "them, and resistance opposes that flow. Ohm's law ties them together: V = I × R — the "
                      "single most-used relationship in basic electronics and when reading instrumentation on "
                      "the floor."),
    },
    "phys-04": {
        "image": "media/book_figures/giant-molecules-materials-science-carrah-p114-x309.png",
        "image_caption": "Folded, aligned polymer chains form stiff crystalline regions",
        "web_notes": ("A polymer's properties come from how its long chains are arranged. Tightly folded, "
                      "aligned chains form crystalline regions that are stiff and strong; tangled random coils "
                      "form amorphous regions that are flexible and tough. The crystalline-to-amorphous ratio "
                      "is what makes one plastic rigid and another rubbery."),
    },
}


def main():
    # group by source file
    index = json.loads((CONTENT / "index.json").read_text())
    file_of = {m: index["modules"][m]["file"] for m in index["module_order"]}
    # map topic_id -> module by scanning files
    applied = 0
    for module, fname in file_of.items():
        path = CONTENT / fname
        data = json.loads(path.read_text())
        changed = False
        for t in data["topics"]:
            if t["id"] in MEDIA:
                t["media"] = MEDIA[t["id"]]
                changed = True
                applied += 1
                print(f"  + {t['id']:<10} {MEDIA[t['id']]['image']}")
        if changed:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    missing = set(MEDIA) - {tid for tid in MEDIA}  # placeholder
    print(f"\nApplied media to {applied}/{len(MEDIA)} topics.")


if __name__ == "__main__":
    main()

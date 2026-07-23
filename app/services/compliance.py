"""
Compliance Rule Engine — GRI / SASB / ESG Heuristics
16 rules across GRI Universal, GRI Topic, SASB, ESG pillars, Financial consistency.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from app.models.schemas import (
    AnomalyFinding, ComplianceReport, ComplianceScore,
    GRIDisclosure, GRIStatus, ParsedDocument, SASBMetric, Severity,
)


@dataclass
class ComplianceRule:
    rule_id: str
    name: str
    category: str
    severity: Severity
    check: Callable[[ParsedDocument], list[AnomalyFinding]] = field(repr=False)
    frameworks: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)


def _has(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(k.lower() in lower for k in keywords)


def _snippet(text: str, keyword: str, ctx: int = 100) -> str:
    idx = text.lower().find(keyword.lower())
    if idx == -1:
        return ""
    s, e = max(0, idx - ctx // 2), min(len(text), idx + ctx // 2)
    return f"…{text[s:e].strip()}…"


def _find_percentages(text: str) -> list[float]:
    return [float(m.group(1)) for m in re.finditer(r"(\d{1,3}(?:\.\d+)?)\s*%", text)]


# ── GRI Universal ────────────────────────────────────────────────────────────

def _gri_2_1(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["registered", "headquarters", "incorporated", "legal name", "ownership structure"]):
        return [AnomalyFinding(rule_id="GRI-2-1", rule_name="GRI 2-1: Organizational Details Missing",
            severity=Severity.MEDIUM, category="GRI Universal",
            description="GRI 2-1 requires disclosure of legal name, HQ, ownership, and legal form.",
            remediation="Add an 'About the Organization' section.")]
    return []


def _gri_2_22(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["ceo", "chief executive", "message from", "letter from", "sustainability strategy"]):
        return [AnomalyFinding(rule_id="GRI-2-22", rule_name="GRI 2-22: Senior Leader Statement Missing",
            severity=Severity.MEDIUM, category="GRI Universal",
            description="GRI 2-22 requires a statement from the most senior decision-maker on sustainable development.",
            remediation="Include a CEO or Board Chair statement.")]
    return []


def _gri_3_3(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["material", "materiality", "double materiality", "management approach"]):
        return [AnomalyFinding(rule_id="GRI-3-3", rule_name="GRI 3-3: Materiality Assessment Missing",
            severity=Severity.HIGH, category="GRI Universal",
            description="GRI 3-3 requires identification of material topics and management approach.",
            remediation="Conduct and disclose a materiality assessment.")]
    return []


# ── GRI 305 — Emissions ──────────────────────────────────────────────────────

def _gri_305_1(doc: ParsedDocument) -> list[AnomalyFinding]:
    text = doc.raw_text
    if not _has(text, ["scope 1", "scope 2", "ghg", "greenhouse gas", "co2", "tco2e"]):
        return [AnomalyFinding(rule_id="GRI-305-1", rule_name="GRI 305-1/2: GHG Emissions Not Disclosed",
            severity=Severity.HIGH, category="GRI Emissions",
            description="GRI 305-1/2 require Scope 1 and Scope 2 GHG emissions in tCO2e.",
            remediation="Disclose Scope 1/2 emissions with methodology and base year.")]
    quant = re.compile(r"(scope\s*[12]|ghg|co2e?)[^.]{0,80}(\d[\d,]*\.?\d*)\s*(mt|tco2|tonnes?|tons?|kg|metric)", re.I)
    if not quant.search(text):
        return [AnomalyFinding(rule_id="GRI-305-1", rule_name="GRI 305-1/2: Emissions Not Quantified",
            severity=Severity.HIGH, category="GRI Emissions",
            description="Scope emissions mentioned but no quantified figure with units detected.",
            evidence=_snippet(text, "scope"), remediation="Provide tCO2e figures for Scope 1/2.")]
    return []


def _gri_305_3(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["scope 3", "value chain emissions", "upstream", "downstream emissions"]):
        return [AnomalyFinding(rule_id="GRI-305-3", rule_name="GRI 305-3: Scope 3 Not Disclosed",
            severity=Severity.MEDIUM, category="GRI Emissions",
            description="GRI 305-3 requires Scope 3 value chain emissions disclosure.",
            remediation="Disclose Scope 3 by category per GHG Protocol.")]
    return []


# ── GRI 303 — Water ──────────────────────────────────────────────────────────

def _gri_303(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["water withdrawal", "water consumption", "water usage", "megalitres", "water management"]):
        return [AnomalyFinding(rule_id="GRI-303", rule_name="GRI 303-3: Water Withdrawal Not Disclosed",
            severity=Severity.MEDIUM, category="GRI Water",
            description="GRI 303-3 requires total water withdrawal by source.",
            remediation="Disclose water withdrawal in megalitres by source.")]
    return []


# ── GRI 401 — Employment ─────────────────────────────────────────────────────

def _gri_401(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["turnover rate", "employee turnover", "new hires", "headcount", "full-time employees", "fte"]):
        return [AnomalyFinding(rule_id="GRI-401", rule_name="GRI 401-1: Employment Metrics Missing",
            severity=Severity.MEDIUM, category="GRI Social",
            description="GRI 401-1 requires new hires and turnover by age, gender, region.",
            remediation="Disclose headcount, new hires, and turnover rates.")]
    return []


# ── GRI 416 — Customer H&S ───────────────────────────────────────────────────

def _gri_416(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["product safety", "customer health", "health and safety assessment", "product recalls"]):
        return [AnomalyFinding(rule_id="GRI-416", rule_name="GRI 416-1: Customer H&S Not Addressed",
            severity=Severity.LOW, category="GRI Social",
            description="GRI 416-1 requires product/service health & safety impact assessment disclosure.",
            remediation="Include a product safety section.")]
    return []


# ── SASB ──────────────────────────────────────────────────────────────────────

def _sasb_energy(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["energy consumption", "renewable energy", "electricity consumption", "gigajoules", "GJ", "kwh", "mwh"]):
        return [AnomalyFinding(rule_id="SASB-ENE", rule_name="SASB: Energy Consumption Not Disclosed",
            severity=Severity.MEDIUM, category="SASB Environmental",
            description="SASB requires total energy consumed and % renewable.",
            remediation="Disclose energy in GJ/MWh with renewable percentage.")]
    return []


def _sasb_waste(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["waste generated", "waste diverted", "landfill", "recycling rate", "hazardous waste"]):
        return [AnomalyFinding(rule_id="SASB-WST", rule_name="SASB: Waste Metrics Not Disclosed",
            severity=Severity.LOW, category="SASB Environmental",
            description="SASB expects waste generation and diversion data.",
            remediation="Disclose total waste by disposal method.")]
    return []


# ── ESG Pillars ───────────────────────────────────────────────────────────────

def _esg_governance(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["board of directors", "independent directors", "audit committee", "ethics", "anti-corruption", "code of conduct"]):
        return [AnomalyFinding(rule_id="ESG-GOV-001", rule_name="ESG: Governance Disclosures Missing",
            severity=Severity.HIGH, category="ESG Governance",
            description="ESG reports require board composition, ethics, and anti-corruption disclosures.",
            remediation="Add governance section with board structure and ethics policy.")]
    return []


def _esg_targets(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["net zero", "net-zero", "science-based target", "sbt", "sbti", "carbon neutral", "paris agreement", "1.5"]):
        return [AnomalyFinding(rule_id="ESG-TGT-001", rule_name="ESG: No Net-Zero / SBTi Targets",
            severity=Severity.MEDIUM, category="ESG Environmental",
            description="Investors expect time-bound decarbonisation targets.",
            remediation="Disclose Paris-aligned or SBTi-validated targets.")]
    return []


# ── Financial ─────────────────────────────────────────────────────────────────

def _fin_revenue(doc: ParsedDocument) -> list[AnomalyFinding]:
    pattern = re.compile(r"(?:revenue|net revenue|total revenue)[^\d]{0,30}([\$€£]?\s*\d[\d,]*\.?\d*)", re.I)
    matches = pattern.findall(doc.raw_text)
    amounts = []
    for m in matches:
        try:
            amounts.append(float(re.sub(r"[^\d.]", "", m.replace(",", ""))))
        except ValueError:
            pass
    amounts = [a for a in amounts if a > 0]
    if len(amounts) >= 2 and len(set(amounts)) > 1:
        if (max(amounts) - min(amounts)) / max(amounts) > 0.05:
            return [AnomalyFinding(rule_id="FIN-001", rule_name="Revenue Figure Inconsistency",
                severity=Severity.CRITICAL, category="Financial",
                description=f"Revenue figures differ by >5%: {sorted(set(amounts))}",
                remediation="Reconcile all revenue figures across the document.")]
    return []


def _fin_pct_sum(doc: ParsedDocument) -> list[AnomalyFinding]:
    findings = []
    for m in re.finditer(r"((?:segment|market|allocation|portfolio|revenue breakdown)[^\n]{0,200})", doc.raw_text, re.I | re.DOTALL):
        pcts = _find_percentages(m.group(1))
        if len(pcts) >= 2:
            total = sum(pcts)
            if total > 105 or total < 95:
                findings.append(AnomalyFinding(rule_id="FIN-002", rule_name="Percentage Breakdown ≠ 100%",
                    severity=Severity.HIGH, category="Financial",
                    description=f"Breakdown totals {total:.1f}%.", evidence=f"Percentages: {pcts}",
                    remediation="Verify segment percentages."))
    return findings


def _dis_auditor(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["independent auditor", "assurance statement", "audit opinion", "KPMG", "Deloitte", "EY", "PwC", "Ernst & Young", "CPA"]):
        return [AnomalyFinding(rule_id="DIS-001", rule_name="Missing Auditor / Assurance",
            severity=Severity.HIGH, category="Disclosure",
            description="No independent auditor or assurance provider detected.",
            remediation="Include an independent assurance statement.")]
    return []


def _dis_fls(doc: ParsedDocument) -> list[AnomalyFinding]:
    if not _has(doc.raw_text, ["forward-looking", "forward looking", "safe harbor", "safe harbour"]):
        return [AnomalyFinding(rule_id="DIS-002", rule_name="Missing FLS Disclaimer",
            severity=Severity.LOW, category="Disclosure",
            description="No forward-looking statements disclaimer found.",
            remediation="Add a standard FLS disclaimer.")]
    return []


# ── GRI / SASB Disclosure Mappers ─────────────────────────────────────────────

_GRI_CHECKS = [
    ("GRI 2-1",  "Organizational Details",               ["registered", "headquarters", "legal name"]),
    ("GRI 2-22", "Statement on Sustainable Development",  ["ceo statement", "message from ceo", "sustainability strategy"]),
    ("GRI 3-3",  "Material Topics",                       ["material", "materiality", "double materiality"]),
    ("GRI 305-1","Scope 1 GHG Emissions",                 ["scope 1", "direct emissions"]),
    ("GRI 305-2","Scope 2 GHG Emissions",                 ["scope 2", "indirect energy"]),
    ("GRI 305-3","Scope 3 GHG Emissions",                 ["scope 3", "value chain emissions"]),
    ("GRI 303-3","Water Withdrawal",                      ["water withdrawal", "water consumption"]),
    ("GRI 401-1","New Employee Hires & Turnover",         ["employee turnover", "new hires", "headcount"]),
    ("GRI 416-1","Customer Health & Safety",              ["product safety", "customer health"]),
]

_SASB_CHECKS = [
    ("SASB-ENE-001", "Environmental", "Total Energy Consumed",  ["energy consumption", "gigajoules", "mwh"]),
    ("SASB-H2O-001", "Environmental", "Total Water Withdrawn",  ["water withdrawal", "megalitres"]),
    ("SASB-WST-001", "Environmental", "Total Waste Generated",  ["waste generated", "metric tonnes waste"]),
    ("SASB-SAF-001", "Social",        "Employee Safety (TRIR)", ["trir", "lost time", "safety incidents"]),
    ("SASB-DIV-001", "Social",        "Gender Diversity (%)",   ["women in leadership", "gender diversity", "female employees"]),
]


def _build_gri(doc: ParsedDocument) -> list[GRIDisclosure]:
    text = doc.raw_text
    return [GRIDisclosure(gri_id=gid, title=title,
                           status=GRIStatus.DISCLOSED if _has(text, kw) else GRIStatus.NOT_DISCLOSED,
                           evidence=_snippet(text, kw[0]) if _has(text, kw) else "")
            for gid, title, kw in _GRI_CHECKS]


def _build_sasb(doc: ParsedDocument) -> list[SASBMetric]:
    text = doc.raw_text
    return [SASBMetric(metric_id=mid, category=cat, description=desc,
                        status=GRIStatus.DISCLOSED if _has(text, kw) else GRIStatus.NOT_DISCLOSED)
            for mid, cat, desc, kw in _SASB_CHECKS]


# ── Rule Engine ───────────────────────────────────────────────────────────────

class RuleEngine:
    def __init__(self) -> None:
        self.rules = [
            ComplianceRule("GRI-2-1",     "GRI 2-1",     "GRI Universal",      Severity.MEDIUM,   _gri_2_1),
            ComplianceRule("GRI-2-22",    "GRI 2-22",    "GRI Universal",      Severity.MEDIUM,   _gri_2_22),
            ComplianceRule("GRI-3-3",     "GRI 3-3",     "GRI Universal",      Severity.HIGH,     _gri_3_3),
            ComplianceRule("GRI-305-1",   "GRI 305-1/2", "GRI Emissions",      Severity.HIGH,     _gri_305_1),
            ComplianceRule("GRI-305-3",   "GRI 305-3",   "GRI Emissions",      Severity.MEDIUM,   _gri_305_3),
            ComplianceRule("GRI-303",     "GRI 303",     "GRI Water",          Severity.MEDIUM,   _gri_303),
            ComplianceRule("GRI-401",     "GRI 401",     "GRI Social",         Severity.MEDIUM,   _gri_401),
            ComplianceRule("GRI-416",     "GRI 416",     "GRI Social",         Severity.LOW,      _gri_416),
            ComplianceRule("SASB-ENE",    "SASB Energy", "SASB Environmental", Severity.MEDIUM,   _sasb_energy),
            ComplianceRule("SASB-WST",    "SASB Waste",  "SASB Environmental", Severity.LOW,      _sasb_waste),
            ComplianceRule("ESG-GOV-001", "ESG Gov",     "ESG Governance",     Severity.HIGH,     _esg_governance),
            ComplianceRule("ESG-TGT-001", "ESG Targets", "ESG Environmental",  Severity.MEDIUM,   _esg_targets),
            ComplianceRule("FIN-001",     "Revenue",     "Financial",          Severity.CRITICAL, _fin_revenue),
            ComplianceRule("FIN-002",     "Pct Sum",     "Financial",          Severity.HIGH,     _fin_pct_sum),
            ComplianceRule("DIS-001",     "Auditor",     "Disclosure",         Severity.HIGH,     _dis_auditor),
            ComplianceRule("DIS-002",     "FLS",         "Disclosure",         Severity.LOW,      _dis_fls),
        ]

    def filter_rules(self, frameworks: list[str] | None = None, sectors: list[str] | None = None) -> list[ComplianceRule]:
        """Return rules matching the given frameworks/sectors. Empty/None = run all rules (default behavior)."""
        rules = self.rules
        if frameworks:
            fw_lower = {f.lower() for f in frameworks}
            rules = [r for r in rules if not r.frameworks or {f.lower() for f in r.frameworks} & fw_lower or any(fw in r.category.lower() for fw in fw_lower)]
        if sectors:
            sec_lower = {s.lower() for s in sectors}
            rules = [r for r in rules if not r.sectors or {s.lower() for s in r.sectors} & sec_lower]
        return rules


_PENALTIES = {Severity.CRITICAL: 25.0, Severity.HIGH: 10.0, Severity.MEDIUM: 5.0, Severity.LOW: 2.0, Severity.INFO: 0.0}
_CAT_IDS = {
    "esg": ["GRI-305-1","GRI-305-3","GRI-303","GRI-401","ESG-GOV-001","ESG-TGT-001","SASB-ENE","SASB-WST"],
    "financial": ["FIN-001","FIN-002"],
    "disclosure": ["DIS-001","DIS-002","GRI-2-1","GRI-2-22","GRI-3-3"],
}


class ComplianceChecker:
    def __init__(self, rule_engine: RuleEngine) -> None:
        self._engine = rule_engine

        def check(self, doc: ParsedDocument, frameworks: list[str] | None = None, sectors: list[str] | None = None) -> tuple[list[AnomalyFinding], ComplianceScore, list[GRIDisclosure], list[SASBMetric]]:
        findings: list[AnomalyFinding] = []
        active_rules = self._engine.filter_rules(frameworks, sectors)
        for rule in active_rules:
            try:
                findings.extend(rule.check(doc))
            except Exception as exc:  # noqa: BLE001
                findings.append(AnomalyFinding(rule_id=rule.rule_id, rule_name=rule.name,
                    severity=Severity.INFO, category=rule.category, description=f"Rule error: {exc}"))
        score = self._score(findings)
        return findings, score, _build_gri(doc), _build_sasb(doc)

    def _score(self, findings: list[AnomalyFinding]) -> ComplianceScore:
        counts = Counter(f.severity for f in findings)
        penalty = sum(_PENALTIES.get(f.severity, 0) for f in findings)
        def _cat(ids: list[str]) -> float:
            return max(0, round(100 - sum(_PENALTIES.get(f.severity, 0) for f in findings if f.rule_id in ids), 1))
        return ComplianceScore(
            overall=max(0, round(100 - penalty, 1)),
            esg=_cat(_CAT_IDS["esg"]), financial=_cat(_CAT_IDS["financial"]), disclosure=_cat(_CAT_IDS["disclosure"]),
            critical_count=counts.get(Severity.CRITICAL, 0), high_count=counts.get(Severity.HIGH, 0),
            medium_count=counts.get(Severity.MEDIUM, 0), low_count=counts.get(Severity.LOW, 0),
            info_count=counts.get(Severity.INFO, 0),
        )

    def build_report(self, doc: ParsedDocument, findings: list[AnomalyFinding], score: ComplianceScore,
                     gri: list[GRIDisclosure], sasb: list[SASBMetric],
                     llm_gap_summary: str = "", analysis_ms: float = 0.0) -> ComplianceReport:
        return ComplianceReport(document_name=doc.filename, parsed=doc, findings=findings,
            gri_disclosures=gri, sasb_metrics=sasb, score=score,
            frameworks_applied=["GRI Universal", "GRI 305/303/401/416", "SASB", "ESG Pillars"],
            llm_gap_summary=llm_gap_summary, analysis_duration_ms=round(analysis_ms, 2))

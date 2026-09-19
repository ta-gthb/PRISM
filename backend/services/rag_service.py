"""
RAG (Retrieval-Augmented Generation) service for legal knowledge.

Provides keyword-based retrieval over a curated knowledge base of LM (PC)
Rules, 2011 provisions.  In a production deployment with GPU resources,
replace the scoring function with sentence-transformers + FAISS for
semantic similarity search.
"""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Knowledge base — key provisions of LM (PC) Rules, 2011
# ---------------------------------------------------------------------------

LEGAL_KB: List[Dict[str, str]] = [
    {
        "rule": "Rule 2(l)",
        "text": (
            "Consumer care number: Every pre-packaged commodity shall bear the name, "
            "address and telephone number or e-mail address of a person or organisation "
            "responsible for handling consumer complaints."
        ),
    },
    {
        "rule": "Rule 4(1)",
        "text": (
            "Maximum Retail Price: Every pre-packaged commodity shall bear the MRP "
            "inclusive of all taxes. The declaration must carry the letters 'MRP' or "
            "'Maximum Retail Price' followed by the price in numerals."
        ),
    },
    {
        "rule": "Rule 4(2)",
        "text": (
            "MRP format: The MRP value must be expressed as a numeral and shall "
            "include all taxes. It must be clearly legible and printed in a "
            "conspicuous manner on the principal display panel."
        ),
    },
    {
        "rule": "Rule 6(1)",
        "text": (
            "Manufacturer details: Name and complete address of the manufacturer, "
            "packer or importer, as the case may be, shall be declared on every "
            "package of a pre-packaged commodity."
        ),
    },
    {
        "rule": "Rule 6(2)",
        "text": (
            "Country of origin: For imported packages, the country of origin or "
            "manufacture must be declared on the label. Failure to declare this is "
            "a major violation."
        ),
    },
    {
        "rule": "Rule 6(5)",
        "text": (
            "Batch/Lot number: Every package shall carry a batch number, lot number "
            "or code number to identify the lot from which the product was manufactured "
            "or packed for traceability purposes."
        ),
    },
    {
        "rule": "Rule 6(6)",
        "text": (
            "Date of manufacture: Month and year in which the commodity is manufactured, "
            "packed or imported shall be stated on the label. For perishables, an expiry "
            "date or best-before date must also be indicated."
        ),
    },
    {
        "rule": "Rule 7(1)",
        "text": (
            "Net quantity: The net quantity in terms of standard units of weights and "
            "measures shall be declared on the label. For solids: by weight. "
            "For liquids: by volume. For articles sold by count: by number."
        ),
    },
    {
        "rule": "Rule 7(2)",
        "text": (
            "Metric units: Net quantity must be declared using the metric system — "
            "kilograms (kg), grams (g), litres (l) or millilitres (ml) as appropriate. "
            "Non-standard units are not permitted."
        ),
    },
    {
        "rule": "Rule 11",
        "text": (
            "Principal display panel: All mandatory declarations shall appear on the "
            "principal display panel of the package in a conspicuous manner. They must "
            "be legible, indelible and printed in a colour contrasting with the background."
        ),
    },
    {
        "rule": "Rule 13",
        "text": (
            "Size of numerals: The size of numerals used for declaring net quantity "
            "shall be in accordance with the schedule provided — larger packages require "
            "larger numeral sizes to ensure readability."
        ),
    },
    {
        "rule": "Rule 18",
        "text": (
            "Penalty: Any person who contravenes or attempts to contravene the provisions "
            "of these rules shall be punishable under Section 36 of the Legal Metrology "
            "Act, 2009 with a fine that may extend to Rs 25,000 for the first offence "
            "and Rs 50,000 for subsequent offences."
        ),
    },
    {
        "rule": "Rule 19",
        "text": (
            "Offences by companies: Where an offence under these rules has been committed "
            "by a company, every person in charge of and responsible for the company shall "
            "be deemed to be guilty and liable to be proceeded against."
        ),
    },
    {
        "rule": "Section 2(l) LMA 2009",
        "text": (
            "Pre-packaged commodity: A commodity that, without the purchaser being present, "
            "is placed in a package of whatever nature such that the quantity of product "
            "contained therein has a predetermined value and cannot be altered without "
            "the package being opened or perceptibly modified."
        ),
    },
    {
        "rule": "Rule 6(10)",
        "text": (
            "E-Commerce marketplace declarations: An e-commerce entity shall ensure that the mandatory declarations "
            "prescribed under Rule 6(1) — including name and address of the manufacturer, packer, or importer, net quantity, "
            "maximum retail price (MRP), country of origin, best before or expiry date, and consumer care details — are "
            "displayed on the digital listing of the commodity. Failure to display these digital declarations is an offence "
            "under the Legal Metrology Act, 2009 and Consumer Protection (E-Commerce) Rules, 2020."
        ),
    },
    {
        "rule": "Rule 9 / Pre-Press Artwork",
        "text": (
            "Packaging artwork design files: Pre-print proofs, dielines, and digital label layouts must satisfy the "
            "proportional Principal Display Panel (PDP) area requirements, minimum font height mandates under the First Schedule, "
            "color contrast ratios against substrate backgrounds, and standard metric unit symbols ('g', 'kg', 'ml', 'l') "
            "prior to commercial printing and manufacturing."
        ),
    },
]


class RAGService:
    """
    Retrieval service for legal knowledge.

    retrieve() scores each knowledge-base document by token overlap with the
    query and returns the top-k results.  For production workloads, swap the
    scorer for a FAISS nearest-neighbour search over sentence-transformer
    embeddings.
    """

    def __init__(self):
        self.kb = LEGAL_KB
        # Build an inverted index: token -> list of doc indices
        self._index: Dict[str, List[int]] = {}
        for i, doc in enumerate(self.kb):
            for token in self._tokenise(doc["rule"] + " " + doc["text"]):
                self._index.setdefault(token, []).append(i)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenise(text: str) -> List[str]:
        import re
        return [t.lower() for t in re.findall(r"[a-z0-9]+", text, re.IGNORECASE)
                if len(t) > 2]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        """Return the top-k most relevant knowledge-base documents."""
        query_tokens = set(self._tokenise(query))
        scores: Dict[int, int] = {}
        for token in query_tokens:
            for doc_idx in self._index.get(token, []):
                scores[doc_idx] = scores.get(doc_idx, 0) + 1

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [self.kb[idx] for idx, _ in ranked[:top_k]]

    def explain_violation(self, rule_code: str, field: str, issue: str) -> str:
        """
        Retrieve the best-matching legal text for a specific violation and
        return a formatted explanation string.
        """
        query = f"{rule_code} {field} {issue}"
        docs = self.retrieve(query, top_k=2)
        if not docs:
            return (
                f"Refer to Legal Metrology (Packaged Commodities) Rules, 2011 "
                f"— {rule_code}."
            )
        return " | ".join(f"[{d['rule']}] {d['text']}" for d in docs)

    def get_compliance_guidance(self, violations: List[Dict]) -> str:
        """
        Build a human-readable guidance block for a set of violations.
        Shows the top 3 violations with retrieved legal context.
        """
        if not violations:
            return (
                "Label is compliant with all checked provisions of "
                "LM (PC) Rules, 2011."
            )

        lines: List[str] = [
            "Compliance guidance based on LM (PC) Rules, 2011:\n"
        ]
        # Prioritise critical > major > minor
        priority = {"critical": 0, "major": 1, "minor": 2}
        sorted_violations = sorted(
            violations,
            key=lambda v: (priority.get(v.get("severity", "minor"), 3)),
        )
        for v in sorted_violations[:3]:
            context = self.explain_violation(
                v.get("rule_code", ""),
                v.get("field", ""),
                v.get("issue", ""),
            )
            lines.append(
                f"• [{v.get('severity', '').upper()}] "
                f"{v.get('issue', '')} ({v.get('rule_code', '')})\n"
                f"  {context}"
            )
        return "\n".join(lines)


rag_service = RAGService()

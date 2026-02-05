"""
Compliance pipeline engine.

Orchestrates: Asset → Models → Signals → Rule Checking → Violations → Outcome
"""

from typing import List, Tuple, Optional
import sys
import os
import re

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from schemas.models import Asset, Signal, Violation, Outcome, ComplianceStatus, ViolationSeverity, Evidence, SignalType, Verdict
from models.ocr import OCRModel
from models.vision import VisionModel
from models.vlm import VLMModel
from models.embedding import EmbeddingSimilarityModel
import uuid
from datetime import datetime


class CompliancePipeline:
    """
    Main pipeline that processes assets through models and rule checking.
    """
    
    def __init__(self):
        self.ocr_model = OCRModel()
        self.vision_model = VisionModel()
        self.vlm_model = VLMModel()
        self.embedding_model = EmbeddingSimilarityModel()
        self._rules = self._load_rules()
    
    def process(self, asset: Asset) -> Outcome:
        """
        Process an asset through the full compliance pipeline.
        
        Flow:
        1. Extract signals from models (OCR, Vision, VLM)
        2. Check signals against compliance rules
        3. Generate violations with evidence
        4. Calculate risk score and status
        5. Return outcome
        
        Args:
            asset: Input image asset
            
        Returns:
            Outcome with compliance assessment
        """
        # Step 1: Extract signals from all models
        signals = self._extract_signals(asset)
        
        # Step 2: Check rules and generate violations
        violations = self._check_rules(asset, signals)
        
        # Step 3: Calculate risk score based on violation confidence
        risk_score = self._calculate_risk_score(violations)
        
        # Step 4: Determine status
        status = self._determine_status(risk_score, violations)

        # Step 4.5: Confidence-based routing at aggregation stage
        rule_confidence = self._calculate_rule_confidence(violations)
        confidence_threshold = 0.85
        routing_flag = None
        if rule_confidence < confidence_threshold:
            routing_flag = "borderline_requires_context"
            status = ComplianceStatus.REVIEW_REQUIRED
        
        # Step 5: Determine verdict
        verdict = self._determine_verdict(risk_score)
        
        # Step 6: Generate fix suggestions
        fix_suggestions = self._generate_fix_suggestions(violations)

        # Step 6.5: VLM escalation (API) for borderline cases only
        self._maybe_attach_vlm_reasoning(asset, signals, violations, routing_flag, verdict, risk_score)
        
        # Step 7: Create outcome
        outcome = Outcome(
            outcome_id=str(uuid.uuid4()),
            asset_id=asset.image_id,
            status=status,
            risk_score=risk_score,
            verdict=verdict,
            violations=violations,
            signals=signals,
            fix_suggestions=fix_suggestions,
            processed_at=datetime.now()
        )

        if routing_flag:
            outcome.metadata["routing"] = routing_flag
        
        return outcome
    
    def _extract_signals(self, asset: Asset) -> List[Signal]:
        """Extract signals from all models."""
        signals = []
        
        # Run OCR
        ocr_signals = self.ocr_model.extract_text(asset.image_data)
        signals.extend(ocr_signals)
        
        # Run vision models
        object_detections = self.vision_model.detect_objects(asset.image_data)
        for det in object_detections:
            bbox = det.get("bbox")
            bounding_box = None
            if isinstance(bbox, list) and len(bbox) == 4:
                bounding_box = {"x": bbox[0], "y": bbox[1], "width": bbox[2], "height": bbox[3]}

            signals.append(
                Signal(
                    signal_id=str(uuid.uuid4()),
                    signal_type=SignalType.OBJECT,
                    source_model=det.get("model", "grounding_dino"),
                    confidence=float(det.get("confidence", 0.0)),
                    raw_data=det,
                    bounding_box=bounding_box,
                    detected_at=datetime.now(),
                )
            )
        
        face_signals = self.vision_model.detect_faces(asset.image_data)
        signals.extend(face_signals)
        
        brand_signals = self.vision_model.detect_brands(asset.image_data)
        signals.extend(brand_signals)
        
        # Run VLM for contextual analysis
        vlm_signals = self.vlm_model.analyze_content(asset.image_data)
        signals.extend(vlm_signals)
        
        # Use VLM to check compliance context
        context_signals = self.vlm_model.check_compliance_context(asset.image_data, signals)
        signals.extend(context_signals)

        # Embedding similarity vs regulation texts (emit only when similarity > threshold)
        embedding_signals = self.embedding_model.extract_similarity(asset.image_data)
        signals.extend(embedding_signals)
        
        return signals
    
    def _check_rules(self, asset: Asset, signals: List[Signal]) -> List[Violation]:
        """
        Check signals against compliance rules.
        
        This is where rule matching happens. Rules check for:
        - Prohibited text claims
        - Misleading or exaggerated claims
        - Restricted objects/scenes
        - Brand usage violations
        - Contextual violations
        """
        violations = []
        
        # Check text signals against all rules
        text_signals = [s for s in signals if s.signal_type == SignalType.TEXT]
        vision_object_signals = [
            s for s in signals
            if s.raw_data.get("type") == "vision_object"
        ]
        embedding_signals_by_regulation = {}
        for s in signals:
            if s.raw_data.get("type") != "image_embedding_similarity":
                continue
            reg = s.raw_data.get("regulation")
            if not reg:
                continue
            embedding_signals_by_regulation.setdefault(reg, []).append(s)

        # Vision → policy evidence mapping (supporting evidence ONLY)
        vision_support_map = {
            "medical_health_claims": {"pill", "medicine", "syringe"},
            "misleading_exaggerated_claims": {"money", "cash", "banknote"},
            "fraud_scams_deceptive": {"money", "cash", "banknote"},
            "financial_products_and_guarantees": {"money", "cash", "banknote"},
            "cryptocurrency_services": {"money", "cash", "banknote"},
        }
        
        # Group violations by rule_id to avoid duplicates
        # Each rule can have multiple matching signals
        rule_matches = {}  # rule_id -> list of (signal, match_info, confidence)
        
        for signal in text_signals:
            text_content = signal.raw_data.get("text", "").lower()
            
            # Check against all rules
            for rule_id, rule in self._rules.items():
                match_result = self._matches_rule(text_content, rule)
                if match_result:
                    matched_term, confidence = match_result
                    if rule_id not in rule_matches:
                        rule_matches[rule_id] = []
                    rule_matches[rule_id].append((signal, matched_term, confidence))
        
        # Vision-primary triggers: rules that can be triggered by vision_object alone
        vision_triggered_rules = {}  # rule_id -> list of (vision Signal,)
        for rule_id, rule in self._rules.items():
            primary_labels = rule.get("vision_primary_labels")
            if not primary_labels:
                continue
            allowed = {str(l).strip().lower() for l in primary_labels}
            matched = [
                s for s in vision_object_signals
                if str(s.raw_data.get("label", "")).strip().lower() in allowed
            ]
            if matched:
                vision_triggered_rules[rule_id] = matched
        
        # For vision-primary rules, only create violations when vision fired (not OCR alone)
        vision_primary_rule_ids = {r for r, rule in self._rules.items() if rule.get("vision_primary_labels")}
        ocr_triggered_ids = set(rule_matches.keys()) - vision_primary_rule_ids
        all_violation_rule_ids = ocr_triggered_ids | set(vision_triggered_rules.keys())
        
        # Create violations from OCR and/or vision matches
        for rule_id in all_violation_rule_ids:
            rule = self._rules[rule_id]
            matches = rule_matches.get(rule_id, [])
            vision_signals = vision_triggered_rules.get(rule_id, [])
            rule = self._rules[rule_id]
            
            # Build evidence: OCR (from rule_matches or secondary for vision-triggered) + vision (if vision-primary)
            evidence_list = []
            for signal, matched_term, confidence in matches:
                evidence = Evidence(
                    evidence_id=str(uuid.uuid4()),
                    violation_id="",  # Will be set after violation creation
                    signal_id=signal.signal_id,
                    evidence_type="text_match",
                    description=f"{rule['name']} detected: '{matched_term}'",
                    data={
                        "matched_text": signal.raw_data.get("text", ""),
                        "matched_term": matched_term,
                        "confidence": confidence,
                        "signal_confidence": signal.confidence,
                        "ocr_text": signal.raw_data.get("text", ""),
                        "bbox": signal.bounding_box
                    }
                )
                evidence_list.append(evidence)
            # Vision-primary: add vision_object evidence (trigger)
            for s in vision_signals:
                evidence_list.append(
                    Evidence(
                        evidence_id=str(uuid.uuid4()),
                        violation_id="",
                        signal_id=s.signal_id,
                        evidence_type="vision_object",
                        description=f"Prohibited object detected: {s.raw_data.get('label')}",
                        data={
                            "label": s.raw_data.get("label"),
                            "confidence": 1.0,
                            "signal_confidence": s.confidence,
                            "bbox": s.raw_data.get("bbox"),
                            "model": s.raw_data.get("model", "grounding_dino"),
                        },
                    )
                )
            # Vision-triggered only: attach any OCR matches as secondary evidence
            if vision_signals and not matches:
                for signal in text_signals:
                    text_content = signal.raw_data.get("text", "").lower()
                    match_result = self._matches_rule(text_content, rule)
                    if match_result:
                        matched_term, confidence = match_result
                        evidence_list.append(
                            Evidence(
                                evidence_id=str(uuid.uuid4()),
                                violation_id="",
                                signal_id=signal.signal_id,
                                evidence_type="text_match",
                                description=f"{rule['name']} (OCR): '{matched_term}'",
                                data={
                                    "matched_text": signal.raw_data.get("text", ""),
                                    "matched_term": matched_term,
                                    "confidence": confidence,
                                    "signal_confidence": signal.confidence,
                                    "ocr_text": signal.raw_data.get("text", ""),
                                    "bbox": signal.bounding_box,
                                },
                            )
                        )

            # Add embedding evidence as low-weight support only
            if rule_id == "misleading_exaggerated_claims":
                for signal in embedding_signals_by_regulation.get("misleading_claims", []):
                    evidence = Evidence(
                        evidence_id=str(uuid.uuid4()),
                        violation_id="",  # Will be set after violation creation
                        signal_id=signal.signal_id,
                        evidence_type="image_embedding_similarity",
                        description="Embedding similarity support signal",
                        data={
                            "score": signal.raw_data.get("score", 0.0),
                            "model": signal.raw_data.get("model", "clip_stub"),
                            "confidence": 0.2,
                            "signal_confidence": signal.confidence
                        }
                    )
                    evidence_list.append(evidence)
            if rule_id == "medical_health_claims":
                for signal in embedding_signals_by_regulation.get("medical_health_claims", []):
                    evidence = Evidence(
                        evidence_id=str(uuid.uuid4()),
                        violation_id="",  # Will be set after violation creation
                        signal_id=signal.signal_id,
                        evidence_type="image_embedding_similarity",
                        description="Embedding similarity support signal",
                        data={
                            "score": signal.raw_data.get("score", 0.0),
                            "model": signal.raw_data.get("model", "clip_stub"),
                            "confidence": 0.2,
                            "signal_confidence": signal.confidence,
                        },
                    )
                    evidence_list.append(evidence)
            if rule_id == "fraud_scams_deceptive":
                for signal in embedding_signals_by_regulation.get("fraud_scams_deceptive", []):
                    evidence = Evidence(
                        evidence_id=str(uuid.uuid4()),
                        violation_id="",  # Will be set after violation creation
                        signal_id=signal.signal_id,
                        evidence_type="image_embedding_similarity",
                        description="Embedding similarity support signal",
                        data={
                            "score": signal.raw_data.get("score", 0.0),
                            "model": signal.raw_data.get("model", "clip_stub"),
                            "confidence": 0.2,
                            "signal_confidence": signal.confidence,
                        },
                    )
                    evidence_list.append(evidence)
            if rule_id == "weapons_ammunition_explosives":
                for signal in embedding_signals_by_regulation.get("weapons_ammunition_explosives", []):
                    evidence = Evidence(
                        evidence_id=str(uuid.uuid4()),
                        violation_id="",
                        signal_id=signal.signal_id,
                        evidence_type="image_embedding_similarity",
                        description="Embedding similarity support signal",
                        data={
                            "score": signal.raw_data.get("score", 0.0),
                            "model": signal.raw_data.get("model", "clip_stub"),
                            "confidence": 0.2,
                            "signal_confidence": signal.confidence,
                        },
                    )
                    evidence_list.append(evidence)
            if rule_id == "tobacco_nicotine":
                for signal in embedding_signals_by_regulation.get("tobacco_nicotine", []):
                    evidence = Evidence(
                        evidence_id=str(uuid.uuid4()),
                        violation_id="",
                        signal_id=signal.signal_id,
                        evidence_type="image_embedding_similarity",
                        description="Embedding similarity support signal",
                        data={
                            "score": signal.raw_data.get("score", 0.0),
                            "model": signal.raw_data.get("model", "clip_stub"),
                            "confidence": 0.2,
                            "signal_confidence": signal.confidence,
                        },
                    )
                    evidence_list.append(evidence)
            if rule_id == "gambling":
                for signal in embedding_signals_by_regulation.get("gambling", []):
                    evidence = Evidence(
                        evidence_id=str(uuid.uuid4()),
                        violation_id="",
                        signal_id=signal.signal_id,
                        evidence_type="image_embedding_similarity",
                        description="Embedding similarity support signal",
                        data={
                            "score": signal.raw_data.get("score", 0.0),
                            "model": signal.raw_data.get("model", "clip_stub"),
                            "confidence": 0.2,
                            "signal_confidence": signal.confidence,
                        },
                    )
                    evidence_list.append(evidence)
            if rule_id == "financial_products_and_guarantees":
                for signal in embedding_signals_by_regulation.get("financial_products_and_guarantees", []):
                    evidence = Evidence(
                        evidence_id=str(uuid.uuid4()),
                        violation_id="",
                        signal_id=signal.signal_id,
                        evidence_type="image_embedding_similarity",
                        description="Embedding similarity support signal",
                        data={
                            "score": signal.raw_data.get("score", 0.0),
                            "model": signal.raw_data.get("model", "clip_stub"),
                            "confidence": 0.2,
                            "signal_confidence": signal.confidence,
                        },
                    )
                    evidence_list.append(evidence)
            if rule_id == "cryptocurrency_services":
                for signal in embedding_signals_by_regulation.get("cryptocurrency_services", []):
                    evidence = Evidence(
                        evidence_id=str(uuid.uuid4()),
                        violation_id="",
                        signal_id=signal.signal_id,
                        evidence_type="image_embedding_similarity",
                        description="Embedding similarity support signal",
                        data={
                            "score": signal.raw_data.get("score", 0.0),
                            "model": signal.raw_data.get("model", "clip_stub"),
                            "confidence": 0.2,
                            "signal_confidence": signal.confidence,
                        },
                    )
                    evidence_list.append(evidence)

            # Add vision evidence as supporting evidence ONLY after OCR already matched.
            # Also apply a tiny confidence boost to OCR evidence when relevant vision objects appear.
            if rule_id in vision_support_map and vision_object_signals:
                allowed = vision_support_map[rule_id]
                matched_vision = [
                    s for s in vision_object_signals
                    if str(s.raw_data.get("label", "")).strip().lower() in allowed
                ]
                if matched_vision:
                    # Small capped boost to text-match confidence (does not change logic; only enriches)
                    for ev in evidence_list:
                        if ev.evidence_type != "text_match":
                            continue
                        base = float(ev.data.get("confidence", 0.0))
                        ev.data["confidence"] = min(1.0, base + 0.1)

                    # Attach vision signals as evidence entries (supporting only)
                    for s in matched_vision:
                        evidence_list.append(
                            Evidence(
                                evidence_id=str(uuid.uuid4()),
                                violation_id="",  # Will be set after violation creation
                                signal_id=s.signal_id,
                                evidence_type="vision_object",
                                description=f"Vision object support: {s.raw_data.get('label')}",
                                data={
                                    "label": s.raw_data.get("label"),
                                    "confidence": 1.0,  # evidence weight; detection confidence is in signal_confidence
                                    "signal_confidence": s.confidence,
                                    "bbox": s.raw_data.get("bbox"),
                                    "model": s.raw_data.get("model", "grounding_dino"),
                                },
                            )
                        )
            
            # Calculate overall confidence for the violation
            # Use average of individual match confidences, weighted by signal confidence
            if evidence_list:
                total_confidence = sum(
                    e.data["confidence"] * e.data["signal_confidence"] 
                    for e in evidence_list
                )
                avg_confidence = total_confidence / len(evidence_list)
            else:
                avg_confidence = 0.8  # Default if no evidence
            
            # Create violation
            violation = Violation(
                violation_id=str(uuid.uuid4()),
                rule_id=rule_id,
                rule_name=rule["name"],
                severity=ViolationSeverity(rule["severity"]),
                description=rule["description"],
                evidence=evidence_list
            )
            
            # Update evidence violation_id
            for evidence in violation.evidence:
                evidence.violation_id = violation.violation_id
            
            violations.append(violation)
        
        # Additional rule checks for objects, scenes, etc. would go here
        
        return violations
    
    def _matches_rule(self, text: str, rule: dict) -> Optional[Tuple[str, float]]:
        """
        Check if text matches a rule.
        
        Returns:
            Tuple of (matched_term, confidence) if match found, None otherwise
            confidence is 0.0 to 1.0
        """
        # Exceptions: if text matches any exception pattern/term, do not trigger (e.g. smoking cessation).
        exception_patterns = rule.get("exception_patterns", [])
        for pat in exception_patterns:
            if re.search(pat, text, re.IGNORECASE):
                return None
        exception_terms = rule.get("exception_terms", [])
        text_lower = text.lower()
        for term in exception_terms:
            if term.lower() in text_lower:
                return None

        # Optional: require some context terms be present (used for medical/health claims).
        context_terms = rule.get("context_terms", [])
        if context_terms:
            text_l = text.lower()
            if not any(t.lower() in text_l for t in context_terms):
                return None

        # First check patterns (more specific, higher priority)
        patterns = rule.get("patterns", [])
        for pattern_info in patterns:
            pattern = pattern_info.get("pattern", "")
            confidence = pattern_info.get("confidence", 0.9)
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matched_text = match.group(0)
                return (matched_text, confidence)
        
        # Then check keyword terms
        prohibited_terms = rule.get("prohibited_terms", [])
        for term in prohibited_terms:
            term_lower = term.lower()
            if term_lower in text:
                # Confidence based on exact match vs partial match
                # Exact word match gets higher confidence
                text_with_spaces = f" {text} "
                if f" {term_lower} " in text_with_spaces:
                    return (term, 0.95)  # High confidence for word boundary match
                else:
                    return (term, 0.85)  # Slightly lower for substring match
        
        return None
    
    def _calculate_risk_score(self, violations: List[Violation]) -> float:
        """
        Calculate overall risk score from violations.
        
        Uses violation confidence scores from evidence to compute weighted risk.
        """
        if not violations:
            return 0.0
        
        # Calculate weighted risk based on violation confidence
        total_weighted_risk = 0.0
        total_weight = 0.0
        
        severity_weights = {
            ViolationSeverity.LOW: 0.2,
            ViolationSeverity.MEDIUM: 0.4,
            ViolationSeverity.HIGH: 0.7,
            ViolationSeverity.CRITICAL: 1.0
        }
        
        for violation in violations:
            # Get average confidence from evidence
            if violation.evidence:
                avg_confidence = sum(
                    e.data.get("confidence", 0.8) * e.data.get("signal_confidence", 0.8)
                    for e in violation.evidence
                ) / len(violation.evidence)
            else:
                avg_confidence = 0.8  # Default if no evidence
            
            # Base risk from severity
            base_risk = severity_weights.get(violation.severity, 0.5)
            
            # Weight by confidence
            weighted_risk = base_risk * avg_confidence
            total_weighted_risk += weighted_risk
            total_weight += avg_confidence
        
        # Average weighted risk
        if total_weight > 0:
            base_score = total_weighted_risk / total_weight
        else:
            base_score = 0.5
        
        # Factor in violation count (more violations = higher risk)
        count_factor = min(len(violations) * 0.03, 0.15)
        
        # Factor in severity (presence of HIGH/CRITICAL increases risk)
        has_critical = any(v.severity == ViolationSeverity.CRITICAL for v in violations)
        has_high = any(v.severity == ViolationSeverity.HIGH for v in violations)
        
        if has_critical:
            severity_factor = 0.2
        elif has_high:
            severity_factor = 0.1
        else:
            severity_factor = 0.0
        
        risk_score = min(base_score + count_factor + severity_factor, 1.0)
        return round(risk_score, 3)  # Round to 3 decimal places for stability

    def _calculate_rule_confidence(self, violations: List[Violation]) -> float:
        """
        Calculate overall rule-based confidence from violations.

        Uses evidence confidence and signal confidence as a proxy for
        how reliable the rule-based outcome is.
        """
        if not violations:
            return 1.0

        confidence_values = []
        for violation in violations:
            if violation.evidence:
                violation_conf = sum(
                    e.data.get("confidence", 0.8) * e.data.get("signal_confidence", 0.8)
                    for e in violation.evidence
                ) / len(violation.evidence)
                confidence_values.append(violation_conf)
            else:
                confidence_values.append(0.8)

        if not confidence_values:
            return 0.8

        return round(sum(confidence_values) / len(confidence_values), 3)
    
    def _determine_status(self, risk_score: float, violations: List[Violation]) -> ComplianceStatus:
        """Determine final compliance status."""
        if risk_score == 0.0:
            return ComplianceStatus.COMPLIANT
        elif risk_score >= 0.7:
            return ComplianceStatus.NON_COMPLIANT
        else:
            return ComplianceStatus.REVIEW_REQUIRED
    
    def _determine_verdict(self, risk_score: float, threshold: float = 0.7) -> Verdict:
        """
        Determine verdict based on risk score.
        
        Args:
            risk_score: Calculated risk score (0.0 to 1.0)
            threshold: Threshold for likely_rejected (default: 0.7)
            
        Returns:
            Verdict: likely_rejected if risk_score > threshold, 
                    borderline if 0.3 <= risk_score <= threshold,
                    likely_approved otherwise
        """
        if risk_score > threshold:
            return Verdict.LIKELY_REJECTED
        elif risk_score >= 0.3:
            return Verdict.BORDERLINE
        else:
            return Verdict.LIKELY_APPROVED
    
    def _generate_fix_suggestions(self, violations: List[Violation]) -> List[str]:
        """
        Generate fix suggestions based on violations.
        
        Provides actionable suggestions for fixing compliance issues,
        especially for misleading claims.
        """
        suggestions = []
        seen_rules = set()
        
        for violation in violations:
            rule_id = violation.rule_id
            
            # Avoid duplicate suggestions for the same rule
            if rule_id in seen_rules:
                continue
            seen_rules.add(rule_id)
            
            # Generate rule-specific suggestions
            if rule_id == "misleading_exaggerated_claims":
                # Collect all matched terms from evidence
                matched_terms = set()
                for evidence in violation.evidence:
                    term = evidence.data.get("matched_term", "")
                    if term:
                        matched_terms.add(term.lower())
                
                if matched_terms:
                    terms_list = ", ".join(sorted(matched_terms))
                    suggestions.append(
                        f"Remove or rephrase misleading claims: {terms_list}. "
                        "Replace absolute guarantees with qualified statements."
                    )
                    suggestions.append(
                        "Avoid exaggerated timeframes (e.g., 'instant', 'overnight'). "
                        "Use realistic expectations and timelines."
                    )
                    if any("100%" in term or "%" in term for term in matched_terms):
                        suggestions.append(
                            "Remove percentage-based guarantees. "
                            "Use descriptive language instead of absolute percentages."
                        )
                    if any("lose" in term for term in matched_terms):
                        suggestions.append(
                            "Avoid specific weight loss timeframes. "
                            "Focus on general health benefits rather than rapid results."
                        )
            
            elif rule_id == "biopharma_prohibited_claims":
                suggestions.append(
                    "Remove medical claims that imply cure or guarantee. "
                    "Use language like 'may support' or 'designed to help' instead."
                )
            
            elif rule_id == "finance_prohibited_claims":
                suggestions.append(
                    "Remove financial guarantees and risk-free claims. "
                    "Include appropriate disclaimers about investment risks."
                )
            
            # General suggestion for any violation
            if not suggestions or violation.severity in [ViolationSeverity.HIGH, ViolationSeverity.CRITICAL]:
                suggestions.append(
                    f"Review and revise content to address {violation.rule_name.lower()}. "
                    "Ensure all claims are substantiated and comply with advertising guidelines."
                )
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:5]  # Limit to 5 suggestions

    def _maybe_attach_vlm_reasoning(
        self,
        asset: Asset,
        signals: List[Signal],
        violations: List[Violation],
        routing_flag: Optional[str],
        verdict: Verdict,
        risk_score: float,
    ) -> None:
        """
        Call the VLM only when:
        - routing_flag == "borderline_requires_context"
        - at least one OCR-based violation exists (text_match evidence)
        - NOT for clean ads or clearly rejected ads
        """
        if routing_flag != "borderline_requires_context":
            return
        if not violations:
            return
        if verdict == Verdict.LIKELY_REJECTED or risk_score >= 0.7:
            return

        # Ensure there's at least one OCR-triggered violation (not vision-only / embedding-only)
        has_ocr_violation = any(
            any(ev.evidence_type == "text_match" for ev in v.evidence)
            for v in violations
        )
        if not has_ocr_violation:
            return

        # Collect OCR texts + vision objects for prompt
        ocr_texts = [
            s.raw_data.get("text", "")
            for s in signals
            if s.signal_type == SignalType.TEXT and s.raw_data.get("text")
        ]
        vision_objects = [
            s.raw_data
            for s in signals
            if s.raw_data.get("type") == "vision_object"
        ]

        # Pick one policy to analyze (first OCR-based violation)
        policy_id = next(
            (v.rule_id for v in violations if any(ev.evidence_type == "text_match" for ev in v.evidence)),
            violations[0].rule_id,
        )

        try:
            explanation = self.vlm_model.analyze_image_context(
                image_bytes=asset.image_data,
                ocr_texts=ocr_texts,
                vision_objects=vision_objects,
                policy_id=policy_id,
            )
        except Exception:
            explanation = "VLM analysis unavailable at this time."

        # Attach as evidence only (no enforcement change)
        for violation in violations:
            violation.evidence.append(
                Evidence(
                    evidence_id=str(uuid.uuid4()),
                    violation_id=violation.violation_id,
                    signal_id="vlm_api",
                    evidence_type="vlm_reasoning_stub",
                    description="VLM context analysis (borderline only)",
                    data={"explanation": explanation},
                )
            )
    
    def _load_rules(self) -> dict:
        """
        Load compliance rules.
        
        In production, this would load from a database or config file.
        For now, using simplified rules based on the original text-based rules.
        """
        return {
            "misleading_exaggerated_claims": {
                "name": "Misleading or Exaggerated Claims",
                "severity": "HIGH",
                "description": "Detects misleading or exaggerated advertising claims that may deceive consumers",
                "type": "keyword",
                "prohibited_terms": [
                    "guaranteed",
                    "instant",
                    "100%",
                    "miracle",
                    "overnight",
                    "immediate",
                    "proven",
                    "scientifically proven",
                    "doctor recommended",
                    "clinically proven"
                ],
                "patterns": [
                    {
                        "pattern": r"lose\s+\d+\s+days?",
                        "confidence": 0.9,
                        "description": "Weight loss time claims (e.g., 'lose 10 days')"
                    },
                    {
                        "pattern": r"lose\s+\d+\s+pounds?\s+in\s+\d+\s+days?",
                        "confidence": 0.95,
                        "description": "Specific weight loss claims with timeframes"
                    },
                    {
                        "pattern": r"\d+%\s+(guaranteed|safe|effective)",
                        "confidence": 0.9,
                        "description": "Percentage-based guarantees"
                    }
                ]
            },
            "medical_health_claims": {
                "name": "Medical / Health Claims",
                "severity": "HIGH",
                "description": "Detects unsubstantiated or guaranteed medical/health claims in ad images (OCR-driven)",
                "type": "keyword",
                # Require explicit medical/health context terms to reduce false positives
                "context_terms": [
                    # Conditions / outcomes
                    "pain", "chronic", "inflammation", "symptom", "disease", "condition",
                    # Common health domains
                    "arthritis", "diabetes", "asthma", "eczema", "acne", "psoriasis",
                    "blood pressure", "cholesterol", "heart", "immune",
                    # Mental health
                    "anxiety", "depression", "stress", "sleep", "insomnia",
                    # Weight loss / body outcomes
                    "weight", "weight loss", "lose", "lbs", "lb", "kg", "kgs", "pounds",
                ],
                "prohibited_terms": [
                    "cure",
                    "treat",
                    "heal",
                    "reverse",
                    "guaranteed results",
                    "100% effective",
                    "clinically proven",
                ],
                "patterns": [
                    {
                        "pattern": r"\b(cure|treat|heal|reverse)\b",
                        "confidence": 0.9,
                        "description": "Medical claim verbs (cure/treat/heal/reverse)",
                    },
                    {
                        "pattern": r"\bguaranteed\s+results?\b",
                        "confidence": 0.9,
                        "description": "Guaranteed medical/health results",
                    },
                    {
                        "pattern": r"\bclinically\s+proven\b",
                        "confidence": 0.85,
                        "description": "Clinically proven claim (requires medical context)",
                    },
                    {
                        "pattern": r"\blose\s+\d+\s*(lbs|lb|kg|kgs|pounds?)\s+in\s+\d+\s+days?\b",
                        "confidence": 0.95,
                        "description": "Weight loss claim with timeframe",
                    },
                    {
                        "pattern": r"\b100%\s+effective\b",
                        "confidence": 0.95,
                        "description": "Absolute effectiveness guarantee",
                    },
                ],
            },
            "biopharma_prohibited_claims": {
                "name": "Prohibited Medical Claims",
                "severity": "HIGH",
                "description": "Prohibited medical claims (cure, guaranteed, etc.)",
                "type": "keyword",
                "prohibited_terms": ["cure", "guaranteed", "no side effects", "100% safe", "miracle"]
            },
            "finance_prohibited_claims": {
                "name": "Prohibited Financial Claims",
                "severity": "HIGH",
                "description": "Prohibited investment claims",
                "type": "keyword",
                "prohibited_terms": ["guaranteed returns", "risk-free", "get rich quick", "no risk"]
            },
            "ads_prohibited_claims": {
                "name": "Prohibited Advertising Claims",
                "severity": "MEDIUM",
                "description": "Prohibited advertising claims",
                "type": "keyword",
                "prohibited_terms": ["100% safe", "guaranteed", "miracle"]
            },
            "fraud_scams_deceptive": {
                "name": "Fraud, Scams, and Deceptive Practices",
                "severity": "HIGH",
                "description": "Meta Ads policy: fraud, scams, and deceptive practices (financial deception, urgency tactics, data harvesting, impersonation)",
                "type": "keyword",
                "prohibited_terms": [
                    "guaranteed income",
                    "guaranteed profit",
                    "guaranteed returns",
                    "risk-free profit",
                    "make money while you sleep",
                    "passive income",
                    "act now",
                    "limited time",
                    "final notice",
                    "last chance",
                    "don't miss out",
                    "bank details",
                    "ssn",
                    "social security number",
                    "credit card number",
                    "crypto wallet",
                    "verify your account",
                    "account verification",
                    "account suspended",
                    "verify immediately",
                    "official notice",
                    "government agency",
                    "support team",
                    "account compromised",
                ],
                "patterns": [
                    {"pattern": r"guaranteed\s+(profit|income|return)s?", "confidence": 0.92, "description": "Guaranteed financial claims"},
                    {"pattern": r"risk-free\s+(profit|return|income)", "confidence": 0.92, "description": "Risk-free financial claims"},
                    {"pattern": r"make\s+money\s+while\s+you\s+sleep", "confidence": 0.95, "description": "Passive/easy money claim"},
                    {"pattern": r"act\s+now|limited\s+time|final\s+notice|last\s+chance", "confidence": 0.88, "description": "Urgency/pressure tactics"},
                    {"pattern": r"(bank\s+details?|credit\s+card|ssn|crypto\s+wallet|password)", "confidence": 0.9, "description": "Data harvesting"},
                    {"pattern": r"(account\s+suspended|verify\s+immediately|official\s+notice)", "confidence": 0.9, "description": "Impersonation/urgency"},
                ],
            },
            "weapons_ammunition_explosives": {
                "name": "Weapons, Ammunition, Explosives",
                "severity": "HIGH",
                "description": "Meta Ads policy: prohibited weapons, ammunition, explosives, and weapon accessories (Restricted Goods)",
                "type": "keyword",
                "vision_primary_labels": ["weapon", "gun", "knife", "ammunition", "explosive"],
                "prohibited_terms": [
                    "ammunition",
                    "bullets",
                    "ammo",
                    "explosive",
                    "bomb",
                    "grenade",
                    "firearm for sale",
                    "knife for sale",
                    "combat knife",
                ],
                "patterns": [
                    {"pattern": r"(buy|sell)\s+gun", "confidence": 0.92, "description": "Gun sale language"},
                    {"pattern": r"firearm\s+for\s+sale", "confidence": 0.92, "description": "Firearm sale"},
                    {"pattern": r"knife\s+for\s+sale|combat\s+knife", "confidence": 0.9, "description": "Knife sale/combat"},
                ],
            },
            "tobacco_nicotine": {
                "name": "Tobacco and Nicotine",
                "severity": "HIGH",
                "description": "Meta Ads policy: prohibited promotion of tobacco and nicotine products (Restricted Goods)",
                "type": "keyword",
                "prohibited_terms": [
                    "cigarettes",
                    "cigars",
                    "tobacco",
                    "vape",
                    "vaping",
                    "e-cigarette",
                    "e-cig",
                    "nicotine products",
                    "nicotine pouches",
                    "hookah",
                    "shisha",
                ],
                "patterns": [
                    {"pattern": r"\b(cigarette|cigar)s?\b", "confidence": 0.9, "description": "Tobacco product"},
                    {"pattern": r"\btobacco\b", "confidence": 0.9, "description": "Tobacco"},
                    {"pattern": r"\b(vape|vaping|e-?cigarette)\b", "confidence": 0.9, "description": "Vape/e-cig"},
                    {"pattern": r"nicotine\s+(products?|pouches?)", "confidence": 0.9, "description": "Nicotine product"},
                    {"pattern": r"\b(hookah|shisha)\b", "confidence": 0.9, "description": "Hookah/shisha"},
                ],
                "exception_patterns": [
                    r"quit\s+smoking",
                    r"smoking\s+cessation",
                    r"nicotine\s+replacement\s+therapy",
                    r"stop\s+smoking",
                    r"fda[- ]approved.*(patch|gum|lozenge|therapy)",
                    r"(patch|gum|lozenge)\s+to\s+quit",
                ],
                "exception_terms": [
                    "quit smoking aid",
                    "nicotine replacement therapy",
                    "smoking cessation",
                    "stop smoking aid",
                ],
            },
            "gambling": {
                "name": "Gambling and Betting",
                "severity": "HIGH",
                "description": "Meta Ads policy: restricted gambling and betting promotions (Restricted Goods)",
                "type": "keyword",
                "prohibited_terms": [
                    "betting",
                    "sportsbook",
                    "casino",
                    "wager",
                    "odds",
                    "betting lines",
                    "poker",
                    "blackjack",
                    "roulette",
                    "win money gambling",
                    "real money bets",
                ],
                "patterns": [
                    {"pattern": r"\b(betting|sportsbook|casino|wager)\b", "confidence": 0.9, "description": "Gambling/betting"},
                    {"pattern": r"betting\s+lines?|odds\s+on", "confidence": 0.9, "description": "Betting lines/odds"},
                    {"pattern": r"\b(poker|blackjack|roulette)\b", "confidence": 0.9, "description": "Casino games"},
                    {"pattern": r"real\s+money\s+(bet|gambling)", "confidence": 0.92, "description": "Real money gambling"},
                    {"pattern": r"win\s+money\s+gambling|bet\s+real\s+money", "confidence": 0.92, "description": "Win/bet money"},
                ],
                "exception_patterns": [
                    r"gambling\s+laws?",
                    r"informational\s+(content|about)",
                    r"for\s+fun\b",
                    r"\bfree\s+(to\s+play)?\s*(card\s+)?games?\b",
                    r"no\s+real\s+money",
                    r"no\s+purchase\s+necessary",
                    r"no\s+prizes?",
                ],
                "exception_terms": [
                    "for fun",
                    "free to play",
                    "no real money",
                    "gambling laws",
                    "informational only",
                ],
            },
            "financial_products_and_guarantees": {
                "name": "Financial Products and Guarantees",
                "severity": "HIGH",
                "description": "Meta Ads policy: restricted financial product promotions and guarantees (Financial Products)",
                "type": "keyword",
                "prohibited_terms": [
                    "credit card",
                    "payday loan",
                    "guaranteed approval",
                    "guaranteed returns",
                    "guaranteed profits",
                    "no risk",
                    "risk-free",
                    "instant approval",
                    "pre-approved",
                    "100% approval",
                    "everyone qualifies",
                    "life insurance",
                    "health insurance",
                ],
                "patterns": [
                    {"pattern": r"\b(credit\s+card|loan|mortgage|payday\s+loan)\b", "confidence": 0.9, "description": "Financial product"},
                    {"pattern": r"\b(investment|investing|trading|portfolio)\b", "confidence": 0.9, "description": "Investment"},
                    {"pattern": r"\b(insurance|life\s+insurance|health\s+insurance)\b", "confidence": 0.9, "description": "Insurance"},
                    {"pattern": r"guaranteed\s+(approval|returns?|profits?)", "confidence": 0.92, "description": "Guarantee"},
                    {"pattern": r"\b(no\s+risk|risk-free)\b", "confidence": 0.9, "description": "No risk claim"},
                    {"pattern": r"(instant|pre-?approved)\s+approval|100%\s+approval|everyone\s+qualifies", "confidence": 0.9, "description": "Approval guarantee"},
                ],
                "exception_patterns": [
                    r"learn\s+how\s+\w+",
                    r"educational\s+(content|about)?",
                    r"informational\s+(content|only|about)?",
                    r"financial\s+literacy",
                    r"how\s+\w+\s+works?",
                    r"disclosure\s+(only|statement)",
                    r"what\s+affects\s+\w+",
                ],
                "exception_terms": [
                    "educational content",
                    "informational only",
                    "financial literacy",
                    "for educational purposes",
                ],
            },
            "cryptocurrency_services": {
                "name": "Cryptocurrency Services",
                "severity": "HIGH",
                "description": "Meta Ads policy: restricted promotion of cryptocurrency-related products or services (Financial Products)",
                "type": "keyword",
                "prohibited_terms": [
                    "cryptocurrency",
                    "crypto trading",
                    "crypto exchange",
                    "buy crypto",
                    "sell crypto",
                    "trade crypto",
                    "yield farming",
                    "token sale",
                    "nft marketplace",
                    "crypto wallet",
                ],
                "patterns": [
                    {"pattern": r"\b(cryptocurrency|crypto)\b", "confidence": 0.88, "description": "Crypto term"},
                    {"pattern": r"\b(bitcoin|ethereum|altcoin)\b", "confidence": 0.9, "description": "Cryptocurrency name"},
                    {"pattern": r"crypto\s+(trading|exchange)", "confidence": 0.9, "description": "Crypto trading/exchange"},
                    {"pattern": r"(buy|sell|trade)\s+crypto", "confidence": 0.9, "description": "Buy/sell/trade crypto"},
                    {"pattern": r"\b(staking|yield\s+farming|token\s+sale|ico)\b", "confidence": 0.9, "description": "Crypto product"},
                    {"pattern": r"nft\s+marketplace|crypto\s+wallet", "confidence": 0.9, "description": "NFT/crypto wallet"},
                ],
                "exception_patterns": [
                    r"learn\s+how\s+\w+",
                    r"how\s+(blockchain|crypto)\s+(works?|technology)",
                    r"educational\s+(content|about)?",
                    r"informational\s+(content|only|about)?",
                    r"news\s+(about|on)\b",
                    r"analysis\s+(of|on)\b",
                    r"security\s+warning",
                    r"risk\s+disclosure",
                    r"why\s+it\s+matters",
                    r"blockchain\s+technology\s+works",
                ],
                "exception_terms": [
                    "educational content",
                    "informational only",
                    "security warning",
                    "risk disclosure",
                    "for educational purposes",
                ],
            },
        }

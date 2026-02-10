"""
Validation Engine Module
Validates extracted data against farmer database using fuzzy matching.
"""

import json
import os
import re
import difflib
from db import list_farmers
from dataclasses import dataclass
from typing import Optional, Dict, List, Union
from pathlib import Path

def _ratio(a: str, b: str) -> int:
    if not a or not b:
        return 0
    return int(difflib.SequenceMatcher(None, a, b).ratio() * 100)


def _token_sort_ratio(a: str, b: str) -> int:
    if not a or not b:
        return 0
    a_tokens = " ".join(sorted(a.split()))
    b_tokens = " ".join(sorted(b.split()))
    return _ratio(a_tokens, b_tokens)


@dataclass
class ValidationResult:
    is_valid: bool
    confidence: float
    matched_farmer: Optional[Dict]
    field_matches: Dict
    issues: List[str]
    warnings: List[str]


class ValidationEngine:
    """
    Validates extracted document fields against a farmer database.
    Uses fuzzy matching for names and exact matching for IDs.
    """
    
    def __init__(self, farmer_database: Union[str, list]):
        """
        Initialize with farmer database.
        
        Args:
            farmer_database: Path to JSON file or list of farmer records
        """
        self._db_mode = False
        if isinstance(farmer_database, str):
            if farmer_database.endswith(".db"):
                self._db_mode = True
                self.farmers = list_farmers()
            else:
                with open(farmer_database, 'r', encoding='utf-8') as f:
                    self.farmers = json.load(f)
        else:
            self.farmers = farmer_database

        self._use_rapidfuzz = os.getenv("USE_RAPIDFUZZ", "true").lower() == "true"
        self._fuzz = None
        self._process = None
        if self._use_rapidfuzz:
            from rapidfuzz import fuzz, process
            self._fuzz = fuzz
            self._process = process
        
        # Build lookup indices for faster matching
        self._build_indices()
    
    def _build_indices(self):
        """Build lookup indices for common fields."""
        self.account_index = {}
        self.aadhaar_index = {}
        self.phone_index = {}
        
        for farmer in self.farmers:
            if farmer.get('account_number'):
                self.account_index[farmer['account_number']] = farmer
            if farmer.get('aadhaar'):
                self.aadhaar_index[farmer['aadhaar']] = farmer
            if farmer.get('phone'):
                self.phone_index[farmer['phone']] = farmer
    
    def validate(self, extracted_fields: Dict) -> ValidationResult:
        """
        Validate extracted fields against farmer database.
        
        Args:
            extracted_fields: Dict of extracted document fields
            
        Returns:
            ValidationResult with match details and issues
        """
        if self._db_mode:
            self.farmers = list_farmers()
            self._build_indices()

        issues = []
        warnings = []
        field_matches = {}
        best_match = None
        best_score = 0
        
        # Try exact match on unique identifiers first
        if extracted_fields.get('account_number'):
            acc = extracted_fields['account_number']
            if acc in self.account_index:
                best_match = self.account_index[acc]
                best_score = 100
                field_matches['account_number'] = {
                    'valid': True, 
                    'confidence': 1.0,
                    'match_type': 'exact'
                }
        
        if not best_match and extracted_fields.get('aadhaar'):
            aadhaar = extracted_fields['aadhaar']
            if aadhaar in self.aadhaar_index:
                best_match = self.aadhaar_index[aadhaar]
                best_score = 100
                field_matches['aadhaar'] = {
                    'valid': True,
                    'confidence': 1.0,
                    'match_type': 'exact'
                }
        
        # Fuzzy match on name if no exact match yet
        if not best_match and extracted_fields.get('name'):
            name = extracted_fields['name']
            for farmer in self.farmers:
                score = self._calculate_match_score(extracted_fields, farmer)
                if score > best_score:
                    best_score = score
                    best_match = farmer
        
        # Validate individual field formats
        field_validations = self._validate_field_formats(extracted_fields)
        field_matches.update(field_validations['field_matches'])
        issues.extend(field_validations['issues'])
        
        # Cross-validate with best match
        if best_match and best_score > 60:
            cross_validation = self._cross_validate(extracted_fields, best_match)
            issues.extend(cross_validation['issues'])
            warnings.extend(cross_validation['warnings'])
        elif best_score <= 60 and extracted_fields.get('name'):
            warnings.append(f"No confident match found for '{extracted_fields['name']}'")
        
        # Determine overall validity
        critical_issues = [i for i in issues if not i.startswith("Minor:")]
        is_valid = len(critical_issues) == 0 and best_score >= 60
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=best_score / 100,
            matched_farmer=best_match if best_score >= 60 else None,
            field_matches=field_matches,
            issues=issues,
            warnings=warnings
        )
    
    def _calculate_match_score(self, extracted: Dict, farmer: Dict) -> float:
        """Calculate fuzzy match score between extracted and database record."""
        scores = []
        weights = []
        
        # Name matching (highest weight)
        if extracted.get('name') and farmer.get('name'):
            # Try both original and English name
            name_score = self._token_sort_ratio(
                extracted['name'].lower(),
                farmer['name'].lower()
            )
            
            if farmer.get('name_en'):
                name_score_en = self._token_sort_ratio(
                    extracted['name'].lower(),
                    farmer['name_en'].lower()
                )
                name_score = max(name_score, name_score_en)
            
            scores.append(name_score)
            weights.append(2.0)  # Double weight for name
        
        # Account number (exact or close)
        if extracted.get('account_number') and farmer.get('account_number'):
            if extracted['account_number'] == farmer['account_number']:
                scores.append(100)
            else:
                # Allow for minor typos
                acc_score = self._ratio(
                    extracted['account_number'],
                    farmer['account_number']
                )
                scores.append(acc_score)
            weights.append(1.5)
        
        # Survey number
        if extracted.get('survey_number') and farmer.get('survey_number'):
            survey_score = self._ratio(
                str(extracted['survey_number']),
                str(farmer['survey_number'])
            )
            scores.append(survey_score)
            weights.append(1.0)
        
        # Phone number
        if extracted.get('phone') and farmer.get('phone'):
            if extracted['phone'] == farmer['phone']:
                scores.append(100)
            else:
                scores.append(self._ratio(extracted['phone'], farmer['phone']))
            weights.append(1.0)
        
        if not scores:
            return 0
        
        # Weighted average
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        total_weight = sum(weights)
        return weighted_sum / total_weight
    
    def _validate_field_formats(self, fields: Dict) -> Dict:
        """Validate format of individual fields."""
        issues = []
        field_matches = {}
        
        # Account number format
        if fields.get('account_number'):
            acc = fields['account_number']
            if not self._validate_account_format(acc):
                issues.append(f"Account number format appears invalid: {acc}")
                field_matches['account_number'] = {'valid': False, 'confidence': 0.3}
            else:
                field_matches['account_number'] = {'valid': True, 'confidence': 0.9}
        
        # IFSC code format
        if fields.get('ifsc_code'):
            ifsc = fields['ifsc_code']
            if not self._validate_ifsc(ifsc):
                issues.append(f"IFSC code format invalid: {ifsc}")
                field_matches['ifsc_code'] = {'valid': False, 'confidence': 0.2}
            else:
                field_matches['ifsc_code'] = {'valid': True, 'confidence': 0.95}
        
        # Aadhaar format
        if fields.get('aadhaar'):
            aadhaar = fields['aadhaar']
            if not self._validate_aadhaar(aadhaar):
                issues.append(f"Aadhaar number format invalid: {aadhaar}")
                field_matches['aadhaar'] = {'valid': False, 'confidence': 0.1}
            else:
                field_matches['aadhaar'] = {'valid': True, 'confidence': 0.95}
        
        # Phone format
        if fields.get('phone'):
            phone = fields['phone']
            if not self._validate_phone(phone):
                issues.append(f"Minor: Phone number format unusual: {phone}")
                field_matches['phone'] = {'valid': False, 'confidence': 0.5}
            else:
                field_matches['phone'] = {'valid': True, 'confidence': 0.9}
        
        return {'field_matches': field_matches, 'issues': issues}
    
    def _cross_validate(self, extracted: Dict, farmer: Dict) -> Dict:
        """Cross-validate extracted fields against matched farmer record."""
        issues = []
        warnings = []
        
        # Check account number mismatch
        if extracted.get('account_number') and farmer.get('account_number'):
            if extracted['account_number'] != farmer['account_number']:
                similarity = self._ratio(
                    extracted['account_number'],
                    farmer['account_number']
                )
                if similarity < 90:
                    issues.append(
                        f"Account number mismatch: document shows '{extracted['account_number']}' "
                        f"but database has '{farmer['account_number']}' (similarity: {similarity}%)"
                    )
                else:
                    warnings.append(
                        f"Account number has minor difference (similarity: {similarity}%)"
                    )
        
        # Check name similarity
        if extracted.get('name') and farmer.get('name'):
            name_sim = self._token_sort_ratio(extracted['name'], farmer['name'])
            if name_sim < 70:
                warnings.append(
                    f"Name partially matches: '{extracted['name']}' vs '{farmer['name']}'"
                )
        
        return {'issues': issues, 'warnings': warnings}
    
    def _validate_account_format(self, acc: str) -> bool:
        """Validate Indian bank account number format."""
        if not acc:
            return False
        acc_clean = acc.replace(' ', '').replace('-', '')
        return acc_clean.isdigit() and 9 <= len(acc_clean) <= 18
    
    def _validate_ifsc(self, ifsc: str) -> bool:
        """Validate IFSC code format (4 letters + 0 + 6 alphanumeric)."""
        if not ifsc:
            return False
        return bool(re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc.upper()))
    
    def _validate_aadhaar(self, aadhaar: str) -> bool:
        """Validate Aadhaar format (12 digits)."""
        if not aadhaar:
            return False
        aadhaar_clean = aadhaar.replace(' ', '')
        return aadhaar_clean.isdigit() and len(aadhaar_clean) == 12
    
    def _validate_phone(self, phone: str) -> bool:
        """Validate Indian phone number format."""
        if not phone:
            return False
        phone_clean = phone.replace(' ', '').replace('-', '')
        return bool(re.match(r'^[6-9]\d{9}$', phone_clean))

    def _ratio(self, a: str, b: str) -> int:
        if self._fuzz:
            return self._fuzz.ratio(a, b)
        return _ratio(a, b)

    def _token_sort_ratio(self, a: str, b: str) -> int:
        if self._fuzz:
            return self._fuzz.token_sort_ratio(a, b)
        return _token_sort_ratio(a, b)
    
    def find_similar_farmers(self, name: str, limit: int = 5) -> List[Dict]:
        """Find farmers with similar names (for suggestions)."""
        all_names = []
        for farmer in self.farmers:
            if farmer.get('name'):
                all_names.append((farmer['name'], farmer))
            if farmer.get('name_en'):
                all_names.append((farmer['name_en'], farmer))
        
        if self._process and self._fuzz:
            matches = self._process.extract(
                name,
                [n[0] for n in all_names],
                scorer=self._fuzz.token_sort_ratio,
                limit=limit
            )
            
            results = []
            seen_ids = set()
            for match_name, score, idx in matches:
                farmer = all_names[idx][1]
                if farmer.get('id') not in seen_ids:
                    results.append({
                        'farmer': farmer,
                        'similarity': score
                    })
                    seen_ids.add(farmer.get('id'))
            
            return results

        scored = []
        for name_value, farmer in all_names:
            score = self._token_sort_ratio(name, name_value)
            scored.append((score, farmer))
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        seen_ids = set()
        for score, farmer in scored[:limit]:
            if farmer.get('id') not in seen_ids:
                results.append({'farmer': farmer, 'similarity': score})
                seen_ids.add(farmer.get('id'))

        return results


if __name__ == "__main__":
    # Test with sample data
    sample_farmers = [
        {
            "id": "F001",
            "name": "राजेश कुमार पाटिल",
            "name_en": "Rajesh Kumar Patil",
            "account_number": "12345678901234",
            "ifsc_code": "SBIN0001234",
            "phone": "9876543210"
        }
    ]
    
    validator = ValidationEngine(sample_farmers)
    
    test_fields = {
        "name": "Rajesh Patil",
        "account_number": "12345678901234"
    }
    
    result = validator.validate(test_fields)
    print(f"Valid: {result.is_valid}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Matched: {result.matched_farmer}")
    print(f"Issues: {result.issues}")

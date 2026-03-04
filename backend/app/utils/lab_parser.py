from typing import Dict, List, Any, Optional
import re
import json

class LabParser:
    """
    Senior AI Engineer implementation for robust lab report parsing.
    Features: Whitelist-based extraction, metadata filtering, unit normalization, and alias mapping.
    """

    # 1. Report Type Detection Keywords
    REPORT_TYPES = {
        "CBC": ["hemoglobin", "wbc", "rbc", "platelets", "hematocrit", "mcv", "mch", "cbc"],
        "DIABETES": ["hba1c", "glucose", "fasting", "postprandial", "insulin"],
        "THYROID": ["tsh", "t3", "t4", "anti-tpo", "thyroglobulin"],
        "KFT": ["creatinine", "urea", "bun", "uric acid", "egfr", "kidney"],
        "LFT": ["bilirubin", "alt", "sgpt", "ast", "sgot", "alp", "albumin", "liver"],
        "LIPID": ["cholesterol", "triglycerides", "hdl", "ldl", "vldl"],
        "VITAMIN": ["vitamin d", "vitamin b12", "folate", "ferritin"],
        "DENGUE": ["ns1", "igm", "igg", "dengue"],
        "URINE": ["specific gravity", "ph", "protein", "glucose", "nitrite", "leukocytes"]
    }

    # Whitelist of valid lab markers (canonical names)
    WHITELIST = {
        "HEMOGLOBIN": ["hb", "hemoglobin", "haemoglobin", "hemoglobin (hb)", "hgb"],
        "WBC": ["wbc", "white blood cells", "leukocytes", "wbc count", "total leucocyte count", "tlc", "w.b.c", "w.b.c count"],
        "RBC": ["rbc", "red blood cells", "erythrocytes", "rbc count", "r.b.c"],
        "HCT": ["hct", "hematocrit", "pcv", "packed cell volume"],
        "MCV": ["mcv", "mean corpuscular volume"],
        "MCH": ["mch", "mean corpuscular hemoglobin"],
        "MCHC": ["mchc", "mean corpuscular hemoglobin concentration"],
        "RDW": ["rdw", "rdw-cv", "rdw-sd", "red cell distribution width"],
        "PLATELETS": ["platelets", "plt", "platelet count"],
        "MPV": ["mpv", "mean platelet volume"],
        "NEUTROPHILS": ["neutrophils", "neut", "polymorphs", "neutrophils absolute count"],
        "LYMPHOCYTES": ["lymphocytes", "lymph", "lymphocytes absolute count"],
        "MONOCYTES": ["monocytes", "mono", "monocytes absolute count"],
        "EOSINOPHILS": ["eosinophils", "eos", "eosinophils absolute count"],
        "BASOPHILS": ["basophils", "baso", "basophils absolute count"],
        "GLUCOSE": ["glucose", "sugar", "fbg", "ppbg", "random glucose", "s. glucose (fasting)", "blood sugar", "fasting blood sugar"],
        "HBA1C": ["hba1c", "glycated hemoglobin", "a1c"],
        "CHOLESTEROL": ["cholesterol", "total cholesterol", "serum cholesterol"],
        "TRIGLYCERIDES": ["triglycerides", "tg", "serum triglycerides"],
        "HDL": ["hdl", "hdl cholesterol", "high density lipoprotein"],
        "LDL": ["ldl", "ldl cholesterol", "low density lipoprotein"],
        "VLDL": ["vldl", "vldl cholesterol"],
        "TSH": ["tsh", "thyroid stimulating hormone", "s.tsh"],
        "T3": ["t3", "triiodothyronine", "total t3", "free t3", "ft3"],
        "T4": ["t4", "thyroxine", "total t4", "free t4", "ft4"],
        "CREATININE": ["creatinine", "serum creatinine", "s.creatinine"],
        "UREA": ["urea", "blood urea", "bun", "blood urea nitrogen"],
        "URIC_ACID": ["uric acid", "serum uric acid"],
        "BILIRUBIN": ["bilirubin", "total bilirubin", "direct bilirubin", "indirect bilirubin"],
        "SGOT": ["sgot", "ast", "aspartate aminotransferase"],
        "SGPT": ["sgpt", "alt", "alanine aminotransferase"],
        "ALP": ["alp", "alkaline phosphatase"],
        "ALBUMIN": ["albumin", "serum albumin"],
        "PROTEIN": ["protein", "total protein"],
        "GLOBULIN": ["globulin"],
        "VITAMIN_D": ["vitamin d", "25-hydroxy vitamin d", "vit d"],
        "VITAMIN_B12": ["vitamin b12", "vit b12", "cobalamin"],
        "CALCIUM": ["calcium", "serum calcium"],
        "IRON": ["iron", "serum iron", "tibc"],
        "CRP": ["crp", "c-reactive protein", "c reactive protein"],
        "ESR": ["esr", "erythrocyte sedimentation rate"],
        "POTASSIUM": ["potassium", "k+", "serum potassium"],
        "SODIUM": ["sodium", "na+", "serum sodium"],
        "CHLORIDE": ["chloride", "cl-"],
        "MAGNESIUM": ["magnesium", "mg++", "serum magnesium"],
        "PHOSPHORUS": ["phosphorus", "p", "phosphate"],
        "VITAMIN_C": ["vitamin c", "ascorbic acid"],
        "URINE_PH": ["ph", "urine ph"],
        "URINE_SG": ["specific gravity", "s.g."],
        "URINE_PROTEIN": ["urine protein", "albuminuria"],
        "URINE_GLUCOSE": ["urine glucose", "glycosuria"]
    }

    # 3. Unit Normalization Factors (Value * Factor = Normalized)
    # We normalize to standard international units (SI) or common medical units
    UNIT_MAP = {
        "GLUCOSE": {"mg/dl": 1.0, "mmol/l": 18.01}, # Normalize to mg/dL
        "CHOLESTEROL": {"mg/dl": 1.0, "mmol/l": 38.67}, # Normalize to mg/dL
        "CREATININE": {"mg/dl": 1.0, "umol/l": 0.0113} # Normalize to mg/dL
    }

    # 4. Metadata Blacklist (Ignore these)
    METADATA_IGNORE = [
        "sex", "gender", "age", "collected", "reported", "sample", "patient", 
        "doctor", "lab", "id", "mrn", "ref by", "received", "page", "date",
        "reference range", "reference", "range", "flag", "unit", "result", "test name",
        "patient information", "email address", "age / gender", "vital stats", "vitals",
        "phone", "address", "uhid", "bill no", "referred by", "technician"
    ]

    # 5. Section Headers to Stop Parsing Under (Non-Test Sections)
    STOP_SECTION_HEADERS = [
        "patient information", "email address", "age / gender", "vital stats",
        "vitals", "personal information", "patient details", "medical history"
    ]

    def __init__(self):
        # Build inverse mapping for fast lookup
        self.alias_to_canonical = {}
        for canonical, aliases in self.WHITELIST.items():
            for alias in aliases:
                self.alias_to_canonical[alias.lower()] = canonical

    def detect_report_type(self, text: str) -> str:
        text_lower = text.lower()
        counts = {rtype: 0 for rtype in self.REPORT_TYPES}
        for rtype, keywords in self.REPORT_TYPES.items():
            for kw in keywords:
                if kw in text_lower:
                    counts[rtype] += 1
        
        best_match = max(counts, key=counts.get)
        return best_match if counts[best_match] > 0 else "GENERAL"

    def normalize_unit(self, marker: str, value: float, unit: str) -> Dict[str, Any]:
        # Handle special characters like µ in unit string
        unit_clean = unit.lower().replace(" ", "").replace("µ", "u").replace("μ", "u")
        canonical = self.alias_to_canonical.get(marker.lower(), marker.upper())
        
        if canonical in self.UNIT_MAP and unit_clean in self.UNIT_MAP[canonical]:
            factor = self.UNIT_MAP[canonical][unit_clean]
            normalized_value = round(value * factor, 2)
            # Determine the standard unit for this canonical marker
            standard_unit = "mg/dL" # Default for our mapped items
            return {"value": normalized_value, "unit": standard_unit}
        
        return {"value": value, "unit": unit}

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parses lab report text into structured JSON.
        Now uses finditer to handle text without explicit newlines (common in OCR).
        """
        # STEP 0: Section Filtering (Ignore patient information sections)
        cleaned_text = text
        # Search for all stop headers and find the earliest one
        earliest_match_pos = len(text)
        found_stop = False
        
        for header in self.STOP_SECTION_HEADERS:
            pattern = re.compile(re.escape(header), re.IGNORECASE)
            match = pattern.search(text)
            if match and match.start() < earliest_match_pos:
                earliest_match_pos = match.start()
                found_stop = True
                print(f"✂️ Found stop section header: {header} at pos {match.start()}")
        
        if found_stop:
            print(f"✂️ Filtering out all content starting from position {earliest_match_pos}")
            cleaned_text = text[:earliest_match_pos]
        
        report_type = self.detect_report_type(text) # Use original text for type detection
        results = []
        
        # Regex for Lab Row
        # Improved to handle spaces/newlines in values and vertical layouts
        row_pattern = re.compile(
            r"([a-zA-Z0-9][a-zA-Z \t\-\(\)\/\.\:\&\,\_]{1,45})"  # Test Name (Group 1)
            r"[\s\.\:\=]+"                                   # Space/Newline or separators
            r"(\d+(?:[\s]*\.[\s]*\d+)?)"                    # Value (Group 2) - robust to spaces around dot
            r"[\s]*"                                        # Optional space/newline
            r"([a-zA-Z/%\^\*µμ]+[a-zA-Z/%\d\^\*µμ]*|(?:\d+\^\d+/[a-zA-Zµμ]+)|)\s*" # Unit/Flag (Group 3)
            r"(\(?\d+\.?\d*[\s]*-[\s]*\d+\.?\d*\)?|)\s*"   # Range (Group 4)
            r"([a-zA-Z/%\d\^\*µμ]+|)",                      # Unit/Flag (Group 5)
            re.IGNORECASE
        )

        # Iterate over all matches in the text
        for match in row_pattern.finditer(text):
            name, value_raw, p1, trange, p2 = match.groups()
            
            # Clean value (remove internal spaces/newlines for float conversion)
            value = re.sub(r'[\s\t\n\r]+', '', value_raw)
            if not value or value == ".": continue
            
            # Step 1: Clean and Validate Name
            # Remove trailing symbols often found in OCR
            name_clean = name.strip().rstrip(':').rstrip('.').strip()
            
            # Metadata Filter: Skip if name contains metadata keywords
            if any(meta in name_clean.lower() for meta in self.METADATA_IGNORE):
                continue
                
            # Whitelist Check
            canonical = self.alias_to_canonical.get(name_clean.lower())
            if not canonical:
                # Try more aggressive cleaning
                agg_name = re.sub(r'[\.\:\s]+$', '', name_clean).lower()
                canonical = self.alias_to_canonical.get(agg_name)
            
            if not canonical:
                continue

            # Step 2: Identify Unit and Status from p1 and p2
            unit = ""
            status = "Normal"
            status_keywords = ["high", "low", "abnormal", "h", "l", "*", "normal"]
            
            for p in [p1.strip(), p2.strip()]:
                if not p: continue
                if any(kw == p.lower() for kw in status_keywords):
                    if p.lower() in ["high", "h"]: status = "High"
                    elif p.lower() in ["low", "l"]: status = "Low"
                    elif p.lower() in ["abnormal", "*"]: status = "Abnormal"
                    else: status = "Normal"
                else:
                    if not unit:
                        unit = p

            # Step 3: Format Result
            try:
                val_float = float(value)
                norm = self.normalize_unit(name_clean, val_float, unit)
                
                results.append({
                    "test_name": canonical.replace("_", " ").title(),
                    "value": norm["value"],
                    "unit": norm["unit"],
                    "range": trange.strip() or "N/A",
                    "status": status
                })
            except:
                continue

        # Return structured data
        return {
            "report_type": report_type,
            "tests": results
        }

# Global instance
lab_parser = LabParser()

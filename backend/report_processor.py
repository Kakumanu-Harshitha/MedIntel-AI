import cv2
import io
import re
import os
import numpy as np
import fitz  # PyMuPDF
from PIL import Image
from typing import Optional, List, Dict

from lab_parser import lab_parser

class ReportProcessor:
    def __init__(self):
        # Initialize the OCR reader once to avoid overhead
        self._reader = None

    @property
    def reader(self):
        """Lazy loader for EasyOCR reader."""
        if self._reader is None:
            try:
                # Check if we should skip heavy models (useful for low-memory environments like Render Free Tier)
                if os.getenv("SKIP_HEAVY_MODELS", "false").lower() == "true":
                    print("⏭️ Skipping EasyOCR initialization (SKIP_HEAVY_MODELS is true)")
                    return None

                print("⏳ Loading EasyOCR...")
                import easyocr
                # Using CPU for OCR as per requirements
                self._reader = easyocr.Reader(['en'], gpu=False)
                print("✅ EasyOCR (CPU) initialized for medical report processing.")
            except Exception as e:
                print(f"⚠️ EasyOCR Initialization Warning: {e}")
                self._reader = None
        return self._reader

    def validate_file(self, file_bytes: bytes, filename: str) -> Optional[str]:
        """
        STEP 1: File Validation
        Reject invalid inputs early.
        """
        # 1. File type check
        if not filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            return "Invalid file type. Please upload a PDF or an image (JPG/PNG)."
        
        # 2. File size check (e.g., 10MB)
        if len(file_bytes) > 10 * 1024 * 1024:
            return "File too large. Please upload a report smaller than 10MB."
            
        return None

    def preprocess_image(self, image_np: np.ndarray) -> np.ndarray:
        """
        STEP 2: OCR PREPROCESSING (MANDATORY)
        Improve resolution, convert to Grayscale, Denoise, and Thresholding.
        """
        try:
            # 1. Convert to grayscale
            if len(image_np.shape) == 3:
                gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
            else:
                gray = image_np

            # 2. Improve Resolution (Upscale if small to reach ≈300 DPI equivalent)
            # Assuming standard mobile photo is ~72 DPI, upscale by 4x for 288 DPI
            h, w = gray.shape[:2]
            if w < 2000:
                scale_factor = 2000 / w
                gray = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)

            # 3. Denoising
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

            # 4. Increase Contrast / Adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )

            # 5. Deskew image to fix tilted text
            coords = np.column_stack(np.where(thresh > 0))
            if coords.size > 0:
                angle = cv2.minAreaRect(coords)[-1]
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                
                (h, w) = thresh.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                deskewed = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return deskewed

            return thresh
        except Exception as e:
            print(f"⚠️ Preprocessing Warning: {e}. Using original image.")
            return image_np

    def validate_extracted_text(self, text: str) -> bool:
        """
        STEP 4: OCR VALIDATION (CRITICAL)
        Contains digits AND at least one medical keyword or unit.
        """
        if not text or len(text.strip()) < 10:
            print(f"⚠️ Validation failed: Text too short ({len(text.strip()) if text else 0} chars)")
            return False
            
        # Comprehensive list of medical keywords and units
        medical_identifiers = [
                'hb', 'hemoglobin', 'hgb', 'wbc', 'rbc', 'glucose', 'cholesterol', 'sugar',
                'platelet', 'count', 'range', 'result', 'value', 'cbc', 'lipid',
                'g/dl', 'mg/dl', 'mmol/l', '%', 'cells/ul', 'units/l', 'fl', 'pg',
                'microgram', 'vitamin', 'thyroid', 'tsh', 'creatinine', 'urea',
                'neutrophils', 'lymphocytes', 'monocytes', 'eosinophils', 'basophils',
                'hct', 'pcv', 'mcv', 'mch', 'mchc', 'rdw', 'mpv',
                'bilirubin', 'protein', 'albumin', 'globulin', 'hba1c', 
                'thyroxine', 'triiodothyronine', 't3', 't4', 'alt', 'ast', 'sgpt', 'sgot',
                'alp', 'bun', 'uric acid', 'calcium', 'iron', 'tibc',
                'report', 'patient', 'reference', 'biological', 'interval', 'observed', 'method',
                'specimen', 'collected', 'received', 'reported', 'clinical', 'pathology', 'diagnostic',
                'test', 'result', 'value', 'analysis', 'lab', 'laboratory', 'hospital', 'doctor', 'physician',
                'name', 'age', 'sex', 'gender', 'date'
            ]
        
        text_lower = text.lower()
        has_identifier = any(ident in text_lower for ident in medical_identifiers)
        has_digits = bool(re.search(r'\d+', text))
        
        if not has_identifier or not has_digits:
            reason = ""
            if not has_identifier: reason += "No medical identifiers. "
            if not has_digits: reason += "No digits. "
            print(f"⚠️ Validation failed: {reason} Sample: {text_lower[:200]}...")

        # Valid if it has both digits and medical context
        return has_identifier and has_digits

    def parse_lab_data(self, text: str) -> str:
        """
        Senior AI Engineer Logic: Uses LabParser for robust extraction.
        """
        print(f"🔍 Parsing lab data from text ({len(text)} chars)...")
        parsed = lab_parser.parse(text)
        
        # Requirement: If fewer than 1 valid tests are extracted, return error
        # (Relaxed from 3 to 1 to support single-test reports, but with warning)
        if len(parsed["tests"]) == 0:
            print(f"⚠️ Parser found 0 tests. Sample text: {text[:200]}...")
            return "ERROR: We couldn't find any recognizable lab results in this report. Please ensure it is a valid medical report and the text is legible."
            
        if len(parsed["tests"]) < 3:
            print(f"⚠️ Parser found only {len(parsed['tests'])} tests. This might be a partial or single-test report.")
            
        # Format as string for LLM consumption while keeping structure
        output = [f"REPORT TYPE: {parsed['report_type']}"]
        for test in parsed["tests"]:
            output.append(f"{test['test_name']}: {test['value']} {test['unit']} (Range: {test['range']}) -> {test['status']}")
        
        return "\n".join(output)


    def extract_text_from_image(self, file_bytes: bytes) -> str:
        """
        Extracts text from an image file using EasyOCR with robust fallback.
        """
        if not self.reader:
            return ""
            
        try:
            image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            image_np = np.array(image)
            print(f"📸 Image loaded: {image.size} {image.mode}")
            
            # Attempt 1: Preprocessed image
            processed_img = self.preprocess_image(image_np)
            print("🔍 Running OCR on preprocessed image...")
            results = self.reader.readtext(processed_img)
            text = " ".join([res[1] for res in results])
            print(f"🔍 OCR Attempt 1 found {len(results)} text blocks, {len(text)} chars.")
            
            # Attempt 2: Fallback to original image if validation fails
            if not self.validate_extracted_text(text):
                print("🔄 OCR attempt 1 failed validation. Retrying with original image...")
                results = self.reader.readtext(image_np)
                text = " ".join([res[1] for res in results])
                print(f"🔍 OCR Attempt 2 found {len(results)} text blocks, {len(text)} chars.")
                
            return text.strip()
        except Exception as e:
            print(f"❌ OCR Extraction Error: {e}")
            return ""

    def extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """
        STEP 2 & 3: PDF Type Detection & Extraction
        """
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            
            if len(doc) > 10:
                doc.close()
                return "ERROR: PDF has too many pages. Please upload a report with 10 pages or less."

            full_text = ""
            is_scanned = True
            
            for page in doc:
                page_text = page.get_text().strip()
                if page_text:
                    full_text += page_text + "\n"
                    is_scanned = False
            
            if is_scanned or not full_text.strip():
                print("📄 PDF appears to be scanned. Running OCR pipeline...")
                full_text = ""
                if not self.reader:
                    doc.close()
                    return "ERROR: OCR service unavailable for scanned PDF."
                
                for page in doc:
                    pix = page.get_pixmap(matrix=fitz.Matrix(4.16, 4.16)) 
                    img_bytes = pix.tobytes("png")
                    ocr_text = self.extract_text_from_image(img_bytes)
                    full_text += ocr_text + "\n"
            
            doc.close()
            result = full_text.strip()
            
            if not self.validate_extracted_text(result):
                return "ERROR: We couldn't analyze this report because the text was unclear or unreadable. Please upload the original PDF or a clearer scan."
                
            return self.parse_lab_data(result)
        except Exception as e:
            print(f"❌ PDF Processing Error: {e}")
            return "ERROR: We encountered a problem reading this PDF. Please try uploading a clearer version or the original file."

    def process_report(self, file_bytes: bytes, filename: str) -> Dict[str, str]:
        """
        Unified entry point for report processing.
        Ensures graceful degradation and partial data handling.
        """
        print(f"🚀 Starting process_report for: {filename}")
        validation_error = self.validate_file(file_bytes, filename)
        if validation_error:
            print(f"❌ File validation error: {validation_error}")
            return {"type": "error", "content": validation_error, "filename": filename}

        filename_lower = filename.lower()
        content = ""

        if filename_lower.endswith(".pdf"):
            print(f"📄 Processing PDF: {filename}")
            content = self.extract_text_from_pdf(file_bytes)
        elif filename_lower.endswith((".jpg", ".jpeg", ".png")):
            print(f"📷 Processing Image: {filename}")
            content = self.extract_text_from_image(file_bytes)
            # Mandatory check: digits + keywords
            if not content or not self.validate_extracted_text(content):
                print(f"❌ Image validation failed. Extracted text sample: {content[:100] if content else 'NONE'}")
                content = "ERROR: We couldn't analyze this image because the text was unclear. Please ensure the photo is well-lit and legible."
            else:
                print(f"✅ Image validation passed. Extracted {len(content)} chars.")
                # If OCR passed validation, we MUST provide a response, even if parsing is partial
                content = self.parse_lab_data(content)
        
        print(f"🏁 process_report finished for {filename}. Result type: {'error' if content.startswith('ERROR') else 'success'}")
        if content.startswith("ERROR:"):
            return {"type": "error", "content": content.replace("ERROR: ", ""), "filename": filename}

        return {
            "type": "medical_report_analysis",
            "content": content,
            "filename": filename
        }

# Global instance
report_processor = ReportProcessor()

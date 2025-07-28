!pip install PyMuPDF
import os
import json
import re
import fitz  #PyMuPDF

class AdvancedFeatureExtractor:
    def extract(self, span, page_height, page_width):
        size = span.get('size', 12)
        flags = span.get('flags', 0)
        bbox = span.get('bbox', [0, 0, 0, 0])
        x0, y0, x1, y1 = bbox
        return {
            'font_size': size,
            'bold': bool(flags & 2**4),
            'italic': bool(flags & 2**1),
            'is_upper': span['text'].isupper() and span['text'].isalpha(),
            'caps_ratio': sum(map(str.isupper, span['text'])) / max(1, len(span['text'])),
            'left': x0 / page_width if page_width else 0,
            'width': (x1 - x0) / page_width if page_width else 0,
            'top': y0 / page_height if page_height else 0
        }

    def extract_text_features(self, text):
        features = {
            'length': len(text.strip()),
            'is_title': text.istitle(),
            'is_short': len(text.strip()) < 80,
            'ends_colon': text.strip().endswith(':')
        }
        features['h3_pattern'] = bool(re.match(r'^\d+\.\d+\.\d+', text))
        features['h2_pattern'] = bool(re.match(r'^\d+\.\d+', text))
        features['h1_pattern'] = bool(re.match(r'^(chapter|section)\s+\d+', text, re.I))
        features['bullet_list'] = bool(re.match(r'^(\-|\•|\d+\)|[a-z]\))\s+', text, re.I))
        heading_words = ['introduction', 'summary', 'conclusion', 'contents', 'overview',
                         'abstract', 'challenge', 'mission', 'objective', 'result']
        features['has_heading_word'] = any(w in text.lower() for w in heading_words)
        return features

class HeadingLevelClassifier:
    def __init__(self):
        self.feat = AdvancedFeatureExtractor()

    def classify(self, text, span, page_info, font_sizes):
        visual = self.feat.extract(span, page_info['height'], page_info['width'])
        text_f = self.feat.extract_text_features(text)
        if text_f['h3_pattern']:
            return 'H3', 0.9
        if text_f['h2_pattern']:
            return 'H2', 0.85
        if text_f['h1_pattern']:
            return 'H1', 0.95
        if re.match(r'^第\d+章', text):
            return 'H1', 0.92
        font_size = visual['font_size']
        pct = sum(s <= font_size for s in font_sizes) / len(font_sizes) if font_sizes else 0.5
        if pct > 0.95 and (visual['bold'] or visual['is_upper']) and text_f['is_short']:
            return 'H1', 0.85
        if pct > 0.9 and visual['is_upper'] and text_f['is_short']:
            return 'H1', 0.8
        if (0.75 < pct <= 0.95) and (visual['bold'] or text_f['is_title']):
            if text_f['has_heading_word'] or text_f['h2_pattern']:
                return 'H2', 0.78
            return 'H2', 0.7
        if (0.5 < pct <= 0.8) and (visual['bold'] or text_f['is_short'] or text_f['bullet_list']):
            return 'H3', 0.65
        return 'NONE', 0.1

class PDFOutlineExtractor:
    def __init__(self):
        self.clf = HeadingLevelClassifier()

    def extract_outline(self, pdf_path, page_limit=50):
        doc = fitz.open(pdf_path)
        outline = []
        font_sizes = self._collect_font_sizes(doc)
        for i in range(min(doc.page_count, page_limit)):
            outline += self._extract_headings_on_page(doc[i], i + 1, font_sizes)
        title = self._extract_title(doc)
        doc.close()
        return {'title': title, 'outline': self._clean_outline(outline)}

    def _collect_font_sizes(self, doc):
        sizes = []
        for p in range(min(doc.page_count, 5)):
            for block in doc[p].get_text("dict")['blocks']:
                if "lines" in block:
                    for line in block['lines']:
                        for span in line['spans']:
                            sizes.append(span['size'])
        return sizes if sizes else [12]

    def _extract_headings_on_page(self, page, pageno, font_sizes):
        headings = []
        page_dict = page.get_text("dict")
        page_info = {'width': page.rect.width, 'height': page.rect.height}
        for block in page_dict['blocks']:
            if 'lines' not in block:
                continue
            for line in block['lines']:
                text = "".join(span['text'] for span in line['spans']).strip()
                if not text or len(text) < 3:
                    continue
                if re.fullmatch(r'[\.\-_\•\s]+', text):
                    continue
                if text.lower() in {"version 2014", "may 31, 2014", "international", "board"}:
                    continue
                main_span = max(line['spans'], key=lambda s: s['size'])
                level, conf = self.clf.classify(text, main_span, page_info, font_sizes)
                if level != 'NONE' and conf > 0.6:
                    headings.append({'level': level, 'text': text.strip(), 'page': pageno})
        return headings

    def _extract_title(self, doc):
        meta = doc.metadata
        if meta.get('title') and len(meta['title'].strip()) > 3:
            return meta['title'].strip()
        page = doc[0]
        max_span, maxf = None, 0
        for block in page.get_text("dict")['blocks']:
            if 'lines' in block:
                for line in block['lines']:
                    for span in line['spans']:
                        if span['size'] > maxf and len(span['text'].strip()) > 3:
                            maxf = span['size']
                            max_span = span
        return max_span['text'].strip() if max_span else "Untitled Document"

    def _clean_outline(self, outline):
        seen, cleaned = set(), []
        for h in outline:
            key = (h['level'], h['page'], h['text'].lower())
            if key not in seen:
                seen.add(key)
                cleaned.append(h)
        return cleaned

if __name__ == "__main__":
    INPUT_DIR = "/app/input"
    OUTPUT_DIR = "/app/output"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    extractor = PDFOutlineExtractor()
    for file in os.listdir(INPUT_DIR):
        if file.lower().endswith(".pdf"):
            pdf_path = os.path.join(INPUT_DIR, file)
            result = extractor.extract_outline(pdf_path)
            output_file = os.path.join(OUTPUT_DIR, file.replace(".pdf", ".json"))
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

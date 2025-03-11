import streamlit as st
import PyPDF2
import re
import requests
import time
import json
import pandas as pd
import numpy as np
import networkx as nx
from pyvis.network import Network
from streamlit.components.v1 import html
from io import BytesIO, StringIO
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import altair as alt
from bs4 import BeautifulSoup
import concurrent.futures
from urllib.parse import urljoin, urlparse
import base64
from wordcloud import WordCloud
import bibtexparser
from unidecode import unidecode
import logging
import os

# ตั้งค่าการบันทึกข้อมูล
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# ตั้งค่าหน้า Streamlit
st.set_page_config(page_title="ตัววิเคราะห์เอกสารอ้างอิง", layout="wide")

# เก็บสถานะของกราฟและเอกสารที่เลือก
if "current_doc" not in st.session_state:
    st.session_state.current_doc = None
if "references" not in st.session_state:
    st.session_state.references = []
if "doi_references" not in st.session_state:
    st.session_state.doi_references = []
if "graph_html" not in st.session_state:
    st.session_state.graph_html = None
if "doc_history" not in st.session_state:
    st.session_state.doc_history = {}
if "progress_bar" not in st.session_state:
    st.session_state.progress_bar = st.empty()
if "author_network" not in st.session_state:
    st.session_state.author_network = None
if "keyword_data" not in st.session_state:
    st.session_state.keyword_data = None
if "pdf_extracts" not in st.session_state:
    st.session_state.pdf_extracts = {}
if "language" not in st.session_state:
    st.session_state.language = "th"  # ค่าเริ่มต้นเป็นภาษาไทย
if "cache_dir" not in st.session_state:
    # สร้างโฟลเดอร์สำหรับแคช ถ้ายังไม่มี
    cache_dir = ".cache"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    st.session_state.cache_dir = cache_dir

# ฟังก์ชันช่วยเหลือเกี่ยวกับภาษา
def get_ui_text(key):
    texts = {
        "title": {
            "th": "ตัววิเคราะห์เอกสารอ้างอิง",
            "en": "Reference Document Analyzer"
        },
        "upload_prompt": {
            "th": "อัปโหลดไฟล์ PDF ที่มีเอกสารอ้างอิง",
            "en": "Upload PDF file with references"
        },
        "clear_button": {
            "th": "ล้างข้อมูล",
            "en": "Clear Data"
        },
        "references_list": {
            "th": "รายการเอกสารอ้างอิง",
            "en": "References List"
        },
        "urls_section": {
            "th": "ลิงก์ (URLs)",
            "en": "Links (URLs)"
        },
        "general_references": {
            "th": "เอกสารอ้างอิงทั่วไป",
            "en": "General References"
        },
        "download_analyze": {
            "th": "ดาวน์โหลดและวิเคราะห์",
            "en": "Download and Analyze"
        },
        "download_success": {
            "th": "ดาวน์โหลดและวิเคราะห์สำเร็จ",
            "en": "Download and analysis successful"
        },
        "loading": {
            "th": "กำลังประมวลผล...",
            "en": "Processing..."
        },
        "graph_title": {
            "th": "กราฟความสัมพันธ์ของเอกสารอ้างอิง",
            "en": "Reference Relationship Graph"
        },
        "export_pdf": {
            "th": "ส่งออกกราฟเป็น PDF",
            "en": "Export Graph as PDF"
        },
        "insights_title": {
            "th": "ข้อมูลเชิงลึกจาก References",
            "en": "Insights from References"
        },
        "year_distribution": {
            "th": "การกระจายตัวของ References ตามปีที่ตีพิมพ์",
            "en": "References Distribution by Publication Year"
        },
        "publisher_distribution": {
            "th": "จำนวน References ตามสำนักพิมพ์",
            "en": "References Count by Publisher"
        },
        "publication_year": {
            "th": "ปีที่ตีพิมพ์",
            "en": "Publication Year"
        },
        "references_count": {
            "th": "จำนวน References",
            "en": "References Count"
        },
        "publisher": {
            "th": "สำนักพิมพ์",
            "en": "Publisher"
        },
        "upload_prompt_bibtex": {
            "th": "หรืออัปโหลดไฟล์ BibTeX",
            "en": "Or Upload BibTeX File"
        },
        "upload_prompt_ris": {
            "th": "หรืออัปโหลดไฟล์ RIS (EndNote)",
            "en": "Or Upload RIS File (EndNote)"
        },
        "citation_network": {
            "th": "เครือข่ายการอ้างอิง",
            "en": "Citation Network"
        },
        "author_network": {
            "th": "เครือข่ายผู้แต่ง",
            "en": "Author Network"
        },
        "keyword_analysis": {
            "th": "การวิเคราะห์คำสำคัญ",
            "en": "Keyword Analysis"
        },
        "top_keywords": {
            "th": "คำสำคัญยอดนิยม",
            "en": "Top Keywords"
        },
        "wordcloud": {
            "th": "เมฆคำ",
            "en": "Word Cloud"
        },
        "compare_documents": {
            "th": "เปรียบเทียบเอกสาร",
            "en": "Compare Documents"
        },
        "select_documents": {
            "th": "เลือกเอกสารที่ต้องการเปรียบเทียบ",
            "en": "Select Documents to Compare"
        },
        "common_references": {
            "th": "อ้างอิงที่ใช้ร่วมกัน",
            "en": "Common References"
        },
        "unique_references": {
            "th": "อ้างอิงที่ไม่ซ้ำกัน",
            "en": "Unique References"
        },
        "document_meta": {
            "th": "ข้อมูลเมตาของเอกสาร",
            "en": "Document Metadata"
        },
        "journal": {
            "th": "วารสาร",
            "en": "Journal"
        },
        "authors": {
            "th": "ผู้แต่ง",
            "en": "Authors"
        },
        "no_data": {
            "th": "ไม่พบข้อมูล",
            "en": "No data found"
        },
        "import_from_doi": {
            "th": "นำเข้าจาก DOI",
            "en": "Import from DOI"
        },
        "enter_doi": {
            "th": "ป้อน DOI",
            "en": "Enter DOI"
        },
        "import": {
            "th": "นำเข้า",
            "en": "Import"
        },
        "settings": {
            "th": "การตั้งค่า",
            "en": "Settings"
        },
        "language_setting": {
            "th": "ภาษา",
            "en": "Language"
        },
        "cache_setting": {
            "th": "ล้างแคช",
            "en": "Clear Cache"
        },
        "saved_references": {
            "th": "เอกสารอ้างอิงที่บันทึกไว้",
            "en": "Saved References"
        },
        "save_reference": {
            "th": "บันทึกอ้างอิงนี้",
            "en": "Save this Reference"
        },
        "edit_reference": {
            "th": "แก้ไขอ้างอิง",
            "en": "Edit Reference"
        },
        "update": {
            "th": "อัปเดต",
            "en": "Update"
        },
        "batch_download": {
            "th": "ดาวน์โหลดเอกสารทั้งหมด",
            "en": "Batch Download All Documents"
        },
        "download_selected": {
            "th": "ดาวน์โหลดเอกสารที่เลือก",
            "en": "Download Selected Documents"
        },
        "references_viz": {
            "th": "การวิเคราะห์แบบมีภาพ",
            "en": "Visual Analysis"
        },
        "references_table": {
            "th": "ตารางอ้างอิง",
            "en": "References Table"
        },
        "export_csv": {
            "th": "ส่งออกเป็น CSV",
            "en": "Export as CSV"
        },
        "export_bibtex": {
            "th": "ส่งออกเป็น BibTeX",
            "en": "Export as BibTeX"
        },
        "import_method": {
            "th": "เลือกวิธีนำเข้า",
            "en": "Select Import Method"
        }
    }
    
    if key in texts:
        if st.session_state.language in texts[key]:
            return texts[key][st.session_state.language]
        return texts[key]["en"]  # ใช้ภาษาอังกฤษเป็นค่าเริ่มต้น
    return key

# ฟังก์ชัน API แคช
def get_cache_path(url_or_doi):
    # สร้างชื่อไฟล์ที่ปลอดภัยสำหรับแคช
    safe_name = base64.urlsafe_b64encode(url_or_doi.encode()).decode()
    return os.path.join(st.session_state.cache_dir, f"{safe_name}.pdf")

@st.cache_data(ttl=3600)
def cached_download_content(url):
    # ตรวจสอบแคชก่อน
    cache_path = get_cache_path(url)
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            return f.read(), "ใช้ข้อมูลจากแคช"
    
    # ดาวน์โหลดข้อมูลใหม่
    content, message = download_content(url)
    
    # บันทึกลงแคช ถ้าดาวน์โหลดสำเร็จ
    if content and "สำเร็จ" in message:
        with open(cache_path, 'wb') as f:
            f.write(content)
    
    return content, message

def clear_cache():
    # ล้างไฟล์ในโฟลเดอร์แคชทั้งหมด
    for filename in os.listdir(st.session_state.cache_dir):
        file_path = os.path.join(st.session_state.cache_dir, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            logging.error(f"Error deleting {file_path}: {e}")
    return "ล้างแคชเรียบร้อยแล้ว"

# ฟังก์ชันดึง references จาก PDF (ปรับปรุง)
def extract_references_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    total_pages = len(pdf_reader.pages)
    
    progress_bar = st.session_state.progress_bar.progress(0, text=get_ui_text("loading"))
    
    for i, page in enumerate(pdf_reader.pages):
        text += page.extract_text() + "\n"
        progress = (i + 1) / total_pages
        progress_bar.progress(progress, text=f"{get_ui_text('loading')} {i+1}/{total_pages}")
        time.sleep(0.05)  # จำลองการประมวลผล
    
    # รูปแบบการอ้างอิงที่หลากหลาย
    reference_patterns = [
        r'(?:\[\d+\]\s+.*?(?=\n\[|\n\n|$))',  # รูปแบบ [1] Author...
        r'(?:\d+\.\s+.*?(?=\n\d+\.|\n\n|$))',  # รูปแบบ 1. Author...
        r'(?:^[A-Z][a-z]+,\s+[A-Z]\..*?(?=\n[A-Z][a-z]+,|\n\n|$))',  # รูปแบบ APA
        r'https?://[^\s]+',  # URLs
        r'(?:doi:\s*[^\s]+)'  # DOIs
    ]
    
    all_references = []
    
    for pattern in reference_patterns:
        matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
        all_references.extend(matches)
    
    # ตรวจหาส่วน References/Bibliography
    ref_section_patterns = [
        r'(?:References|Bibliography|REFERENCES|BIBLIOGRAPHY)[\s\n]+([\s\S]+?)(?=\n\s*\n\s*[A-Z]{2,}|\Z)',
        r'(?:อ้างอิง|เอกสารอ้างอิง|บรรณานุกรม)[\s\n]+([\s\S]+?)(?=\n\s*\n\s*[ก-๙]{2,}|\Z)'
    ]
    
    for pattern in ref_section_patterns:
        match = re.search(pattern, text)
        if match:
            ref_section = match.group(1)
            # แยกรายการอ้างอิงตามรูปแบบทั่วไป
            lines = ref_section.split('\n')
            current_ref = ""
            
            for line in lines:
                if re.match(r'^\s*\[\d+\]|\d+\.|\s*[A-Z][a-z]+,\s+[A-Z]\.', line):
                    if current_ref:
                        all_references.append(current_ref.strip())
                    current_ref = line
                else:
                    current_ref += " " + line
            
            if current_ref:  # เพิ่มรายการสุดท้าย
                all_references.append(current_ref.strip())
    
    # ลบรายการที่ซ้ำกัน
    unique_references = []
    for ref in all_references:
        ref = ref.strip()
        if ref and ref not in unique_references:
            unique_references.append(ref)
    
    progress_bar.empty()
    
    return unique_references

# ฟังก์ชันดึง DOI จาก reference (ปรับปรุง)
def extract_doi(ref):
    patterns = [
        r'doi:\s*([^\s,;]+)',
        r'https?://doi.org/([^\s,;]+)',
        r'10\.\d{4,}\/[^\s,;)]+' # รูปแบบ DOI โดยตรง
    ]
    for pattern in patterns:
        doi_match = re.search(pattern, ref, re.IGNORECASE)
        if doi_match:
            doi = doi_match.group(1) if 'doi:' in pattern or 'doi.org' in pattern else doi_match.group(0)
            # ทำความสะอาด DOI
            return doi.strip('.,;:()')
    return None

# ฟังก์ชันดึงปีจาก reference (ปรับปรุง)
def extract_year(ref):
    # รูปแบบปี คศ. ทั่วไป
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', ref)
    if year_match:
        return int(year_match.group(0))
    
    # รูปแบบในวงเล็บ (2020)
    year_paren_match = re.search(r'\((\d{4})\)', ref)
    if year_paren_match:
        return int(year_paren_match.group(1))
    
    # รูปแบบปี พศ.
    be_match = re.search(r'\b(25\d{2})\b', ref)
    if be_match:
        be_year = int(be_match.group(0))
        return be_year - 543  # แปลงจาก พ.ศ. เป็น ค.ศ.
    
    return None

# ฟังก์ชันระบุสำนักพิมพ์จาก DOI (ปรับปรุง)
def extract_publisher(doi):
    if not doi or not isinstance(doi, str) or not doi.startswith("10"):
        return "Unknown"
    
    try:
        doi_prefix = doi.split("/")[0]
        publisher_map = {
            "10.1109": "IEEE",
            "10.1016": "Elsevier",
            "10.1007": "Springer",
            "10.1021": "American Chemical Society",
            "10.1038": "Nature Publishing Group",
            "10.1002": "Wiley",
            "10.1080": "Taylor & Francis",
            "10.1177": "SAGE Publishing",
            "10.3390": "MDPI",
            "10.1371": "Public Library of Science (PLOS)",
            "10.3389": "Frontiers",
            "10.1093": "Oxford University Press",
            "10.1111": "Blackwell Publishing (Wiley)",
            "10.1145": "Association for Computing Machinery (ACM)",
            "10.1088": "IOP Publishing",
            "10.1063": "AIP Publishing",
            "10.1073": "National Academy of Sciences (PNAS)",
            "10.4236": "Scientific Research Publishing",
            "10.1017": "Cambridge University Press",
            "10.5281": "Zenodo",
            "10.5334": "Ubiquity Press",
            "10.3233": "IOS Press",
            "10.5772": "IntechOpen",
            "10.5194": "Copernicus Publications",
            "10.2514": "American Institute of Aeronautics and Astronautics",
            "10.3844": "Science Publications",
            "10.1051": "EDP Sciences",
            "10.4018": "IGI Global",
            "10.1186": "BioMed Central",
            "10.1039": "Royal Society of Chemistry",
            "10.1042": "Portland Press",
            "10.3390": "MDPI"
        }
        return publisher_map.get(doi_prefix, "Other Publisher")
    except:
        return "Unknown"

# ฟังก์ชันดึงชื่อวารสารจาก reference
def extract_journal(ref):
    # พยายามระบุชื่อวารสาร
    patterns = [
        r'(?:[,.]\s+)([A-Z][A-Za-z\s&]+)(?:[,.]\s+(?:Vol|Journal|Conference|Proc|\d{1,2}\(\d{1,2}\)))',
        r'"([^"]+)"(?:[,.]\s+(?:Vol|Journal|\d{1,2}\(\d{1,2}\)))',
        r'\'([^\']+)\'(?:[,.]\s+(?:Vol|Journal|\d{1,2}\(\d{1,2}\)))',
        r'In(?::|.\s+)([A-Z][A-Za-z\s&]+)(?:[,.]\s+(?:Vol|Proceedings|Conference|\d{1,2}\(\d{1,2}\)))'
    ]
    
    for pattern in patterns:
        journal_match = re.search(pattern, ref)
        if journal_match:
            return journal_match.group(1).strip()
    
    # ถ้าไม่พบจากรูปแบบที่ระบุก็ลองเดาจากอักษรตัวใหญ่ที่ติดกัน
    capital_words_match = re.search(r'[,.]\s+([A-Z][A-Z& ]{2,}[a-z]*(?:\s+[A-Z][a-z]+){0,3})[,.]', ref)
    if capital_words_match:
        return capital_words_match.group(1).strip()
    
    # ถ้าไม่พบจากทุกวิธี
    return "Unknown Journal"

# ฟังก์ชันดึงชื่อผู้แต่งจาก reference
def extract_authors(ref):
    # รูปแบบผู้แต่งแบบต่างๆ
    patterns = [
        # [1] Author1, A., Author2, B. (Year)
        r'^\s*(?:\[\d+\])?\s*([A-Za-z,\.\s]+?)(?:\(|\d{4}|Vol|Journal)',
        # Author1, A., & Author2, B. (Year)
        r'^([A-Za-z,\.\s&]+?)(?:\(|\d{4})',
        # Author1, A. and Author2, B. (Year)
        r'^([A-Za-z,\.\s]+?(?:\sand\s)[A-Za-z,\.\s]+?)(?:\(|\d{4})'
    ]
    
    for pattern in patterns:
        author_match = re.search(pattern, ref)
        if author_match:
            authors = author_match.group(1).strip()
            # ทำความสะอาดเล็กน้อย
            authors = re.sub(r'\s+', ' ', authors)
            return authors
    
    return "Unknown Authors"

# ฟังก์ชันแยกชื่อผู้แต่งออกเป็นรายบุคคล
def extract_all_authors(ref):
    authors_text = extract_authors(ref)
    if authors_text == "Unknown Authors":
        return []
    
    # แบ่งตาม patterns ทั่วไป
    authors = []
    
    # แยกด้วย "and" หรือ "&"
    if " and " in authors_text.lower() or "&" in authors_text:
        parts = re.split(r'\s+and\s+|\s+&\s+', authors_text, flags=re.IGNORECASE)
        for part in parts:
            # ตรวจสอบว่าเป็นรายชื่อหลายคนที่คั่นด้วยเครื่องหมายจุลภาค
            if "," in part and not re.search(r'[A-Z]\.,', part):
                commas = part.split(',')
                for i in range(0, len(commas)-1, 2):
                    if i+1 < len(commas):
                        author = f"{commas[i].strip()}, {commas[i+1].strip()}"
                        authors.append(author)
            else:
                authors.append(part.strip())
    else:
        # ถ้าไม่มี and หรือ & ให้ลองแยกด้วยเครื่องหมายจุลภาค
        parts = authors_text.split(',')
        
        i = 0
        while i < len(parts) - 1:
            if re.match(r'^\s*[A-Z]\.', parts[i+1]):
                # ถ้าส่วนต่อไปเริ่มต้นด้วยตัวอักษรตัวใหญ่ตามด้วยจุด น่าจะเป็นชื่อย่อ
                author = f"{parts[i].strip()}, {parts[i+1].strip()}"
                if i+2 < len(parts) and re.match(r'^\s*[A-Z]\.', parts[i+2]):
                    # ถ้ามีชื่อกลางด้วย
                    author += f", {parts[i+2].strip()}"
                    i += 3
                else:
                    i += 2
                authors.append(author)
            else:
                # ไม่ใช่รูปแบบผู้แต่ง ให้ข้ามไป
                i += 1
    
    # ดึงเฉพาะชื่อผู้แต่งที่ดูเหมือนชื่อจริง (มีตัวอักษรมากกว่า 2 ตัว)
    return [author for author in authors if len(author.strip()) > 2]

# ฟังก์ชันดึงชื่อเรื่องจาก reference
def extract_title(ref):
    # ตัดข้อมูลเกี่ยวกับผู้แต่งและปีออกก่อน
    author_year_pattern = r'^(?:\[\d+\]\s*)?(?:[A-Za-z,\.\s&]+?)(?:\(\d{4}\)|\d{4})\s*(.+?)(?:[,\.]\s+(?:In:|Vol|Journal|pp\.|pages|doi:)|$)'
    title_match = re.search(author_year_pattern, ref)
    
    if title_match:
        title = title_match.group(1).strip()
        # ลบเครื่องหมายอัญประกาศออก
        title = title.strip('"\'')
        # ลบจุดท้ายประโยค
        title = title.rstrip('.')
        return title
    
    # ถ้าไม่พบรูปแบบแรก ลองวิธีที่ 2
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', ref)
    if year_match:
        year_pos = year_match.start()
        after_year = ref[year_pos+4:].strip()
        # หาจุดแรกหรือเครื่องหมายจุลภาค
        end_pos = after_year.find('.')
        if end_pos == -1:
            end_pos = after_year.find(',')
        if end_pos != -1:
            title = after_year[:end_pos].strip()
            return title
        else:
            # ถ้าไม่พบเครื่องหมายวรรคตอน ให้ใช้ 10 คำแรก
            words = after_year.split()
            title = ' '.join(words[:min(10, len(words))])
            return title + "..."
    
    return "Unknown Title"

# ฟังก์ชันวิเคราะห์ความถี่ของคำสำคัญ
def analyze_keyword_frequency(references, top_n=20):
    common_words = set([
        'the', 'and', 'of', 'in', 'on', 'for', 'with', 'to', 'a', 'an', 'by', 'is', 'are', 'was', 'were', 
        'that', 'this', 'these', 'those', 'it', 'as', 'at', 'be', 'from', 'has', 'have', 'had', 
        'doi', 'vol', 'volume', 'issue', 'pp', 'page', 'pages', 'journal', 'conference', 'proceedings',
        'international', 'research', 'university', 'year', 'new', 'study', 'analysis', 'author', 'authors',
        'published', 'publication', 'article', 'paper', 'press'
    ])
    
    word_count = {}
    for ref in references:
        # แปลงเป็นตัวพิมพ์เล็ก
        ref_lower = ref.lower()
        # ดึงคำออกมา กรองเฉพาะตัวอักษร
        words = re.findall(r'\b[a-z]{3,}\b', ref_lower)
        for word in words:
            if word not in common_words:
                word_count[word] = word_count.get(word, 0) + 1
    
    # เรียงตามความถี่จากมากไปน้อย และเลือก top_n
    return sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:top_n]

# ฟังก์ชันวิเคราะห์เครือข่ายผู้แต่ง
def analyze_author_network(references):
    # สร้างเครือข่ายของผู้แต่งที่ทำงานร่วมกัน
    author_network = nx.Graph()
    
    for ref in references:
        authors = extract_all_authors(ref)
        if len(authors) > 1:
            for i in range(len(authors)):
                if not author_network.has_node(authors[i]):
                    author_network.add_node(authors[i], count=1)
                else:
                    author_network.nodes[authors[i]]['count'] += 1
                    
                for j in range(i+1, len(authors)):
                    if author_network.has_edge(authors[i], authors[j]):
                        author_network[authors[i]][authors[j]]['weight'] += 1
                    else:
                        author_network.add_edge(authors[i], authors[j], weight=1)
    
    return author_network

# ฟังก์ชันสร้างเครือข่ายผู้แต่งแบบที่ใช้กับ pyvis
def create_author_network_graph(author_network):
    if not author_network or author_network.number_of_nodes() == 0:
        return None
    
    net = Network(height="500px", width="100%", notebook=False)
    
    # คำนวณขนาดของโหนดตามจำนวนผลงาน
    max_count = max([data.get('count', 1) for _, data in author_network.nodes(data=True)])
    min_size = 10
    max_size = 30
    
    # เพิ่มโหนดพร้อมปรับขนาด
    for node, data in author_network.nodes(data=True):
        count = data.get('count', 1)
        size = min_size + (max_size - min_size) * (count / max_count)
        net.add_node(node, title=f"{node} ({count} publications)", size=size, color="#3498db")
    
    # เพิ่มเส้นเชื่อม
    for u, v, data in author_network.edges(data=True):
        weight = data.get('weight', 1)
        net.add_edge(u, v, title=f"Collaborated on {weight} papers", width=weight)
    
    # ปรับการแสดงผล
    net.set_options("""
    var options = {
      "nodes": {
        "shape": "dot",
        "font": {
          "size": 12,
          "face": "Tahoma"
        }
      },
      "edges": {
        "color": {
          "inherit": true
        },
        "smooth": {
          "enabled": false
        }
      },
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": {
          "enabled": true,
          "iterations": 1000
        }
      }
    }
    """)
    
    net.save_graph("author_network.html")
    with open("author_network.html", "r", encoding="utf-8") as f:
        graph_html = f.read()
    
    return graph_html

# ฟังก์ชันดึงลิงก์ PDF จากหน้า HTML
def extract_pdf_link(html_content, base_url):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # แบบที่ 1: หาตามส่วนขยายไฟล์ .pdf
    pdf_links = soup.find_all("a", href=re.compile(r'\.pdf(\?.*)?'))
    
    # แบบที่ 2: หาตาม mime type หรือ class ทั่วไป
    if not pdf_links:
        pdf_links = soup.find_all("a", attrs={"type": "application/pdf"})
    
    # แบบที่ 3: หาจากข้อความลิงก์ทั่วไป
    if not pdf_links:
        pdf_links = soup.find_all("a", text=re.compile(r'PDF|Full Text|Download', re.IGNORECASE))
    
    # แบบที่ 4: หาจาก class ทั่วไปที่มักใช้สำหรับลิงก์ PDF
    if not pdf_links:
        pdf_links = soup.find_all("a", class_=re.compile(r'pdf|full[-_]?text|download', re.IGNORECASE))
    
    for link in pdf_links:
        href = link.get("href")
        if href:
            if href.startswith("http"):
                return href
            else:
                # หากเป็น relative URL ให้รวมกับ base_url
                return urljoin(base_url, href)
    
    return None

# ฟังก์ชันสำหรับ CrossRef API
def query_crossref_api(doi):
    if not doi:
        return None
    
    url = f"https://api.crossref.org/works/{doi}"
    headers = {
        "User-Agent": "ReferenceAnalyzer/1.0 (mailto:user@example.com)",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data['message']
        else:
            return None
    except Exception as e:
        logging.error(f"Error accessing Crossref API: {str(e)}")
        return None

# ฟังก์ชันดาวน์โหลดเนื้อหา (ปรับปรุง)
def download_content(url):
    progress_bar = st.session_state.progress_bar.progress(0, text=get_ui_text("loading"))
    
    try:
        if not url.startswith("http"):
            # ถ้าเป็น DOI ต้องเพิ่ม URL นำหน้า
            if url.startswith("10."):
                url = f"https://doi.org/{url}"
            else:
                return None, "URL ไม่ถูกต้อง: กรุณาตรวจสอบ DOI หรือลิงก์"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        progress_bar.progress(0.2, text=f"{get_ui_text('loading')} - เริ่มการเชื่อมต่อ")
        
        response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        
        progress_bar.progress(0.5, text=f"{get_ui_text('loading')} - ได้รับการตอบสนอง")
        
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "").lower()
            
            if "application/pdf" in content_type:
                progress_bar.progress(1.0, text=f"{get_ui_text('loading')} - ดาวน์โหลดสำเร็จ")
                return response.content, "ดาวน์โหลด PDF สำเร็จ"
            
            elif "text/html" in content_type:
                progress_bar.progress(0.6, text=f"{get_ui_text('loading')} - กำลังค้นหาลิงก์ PDF")
                
                # ใช้ CrossRef API ถ้าเป็น DOI
                if "doi.org" in url:
                    doi = url.split("doi.org/")[1]
                    metadata = query_crossref_api(doi)
                    if metadata and "link" in metadata:
                        for link in metadata.get("link", []):
                            if link.get("content-type") == "application/pdf":
                                pdf_url = link.get("URL")
                                if pdf_url:
                                    pdf_response = requests.get(pdf_url, headers=headers, timeout=20)
                                    if pdf_response.status_code == 200 and "application/pdf" in pdf_response.headers.get("content-type", "").lower():
                                        progress_bar.progress(1.0, text=f"{get_ui_text('loading')} - ดาวน์โหลด PDF สำเร็จ (ผ่าน CrossRef)")
                                        return pdf_response.content, "ดาวน์โหลด PDF สำเร็จจาก CrossRef API"
                
                # พยายามหาลิงก์ PDF จากหน้าเว็บ
                progress_bar.progress(0.7, text=f"{get_ui_text('loading')} - กำลังวิเคราะห์หน้าเว็บ")
                pdf_url = extract_pdf_link(response.text, url)
                
                if pdf_url:
                    progress_bar.progress(0.8, text=f"{get_ui_text('loading')} - พบลิงก์ PDF กำลังดาวน์โหลด")
                    # ดาวน์โหลด PDF จากลิงก์ที่พบ
                    pdf_response = requests.get(pdf_url, headers=headers, timeout=20)
                    if pdf_response.status_code == 200 and "application/pdf" in pdf_response.headers.get("content-type", "").lower():
                        progress_bar.progress(1.0, text=f"{get_ui_text('loading')} - ดาวน์โหลด PDF สำเร็จ")
                        return pdf_response.content, "ดาวน์โหลด PDF สำเร็จจากลิงก์ในหน้าเว็บ"
                    elif pdf_response.status_code == 200:
                        # บางครั้งเซิร์ฟเวอร์อาจไม่ระบุ content-type ที่ถูกต้อง
                        if pdf_response.content.startswith(b'%PDF'):
                            progress_bar.progress(1.0, text=f"{get_ui_text('loading')} - ดาวน์โหลด PDF สำเร็จ")
                            return pdf_response.content, "ดาวน์โหลด PDF สำเร็จจากลิงก์ในหน้าเว็บ"
                        else:
                            return None, "ไม่สามารถยืนยันว่าไฟล์ที่ดาวน์โหลดเป็น PDF"
                    else:
                        return None, f"ไม่สามารถดาวน์โหลด PDF ได้ (สถานะ: {pdf_response.status_code})"
                else:
                    return None, "ไม่พบลิงก์ PDF ในหน้าเว็บ"
            
            else:
                return None, f"ประเภทเนื้อหาไม่รองรับ: {content_type}"
        
        elif response.status_code == 404:
            return None, "ไม่พบทรัพยากร (404): ลิงก์อาจเสียหรือถูกลบ"
        
        elif response.status_code == 403:
            return None, "ถูกปฏิเสธการเข้าถึง (403): อาจต้องล็อกอินหรือใช้ VPN"
        
        else:
            return None, f"ไม่สามารถดาวน์โหลดเนื้อหาได้ (สถานะ: {response.status_code})"
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading content: {str(e)}")
        return None, f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {str(e)}"
    
    finally:
        progress_bar.empty()

# ฟังก์ชันนำเข้า BibTeX
def import_bibtex(bibtex_file):
    text = bibtex_file.read().decode('utf-8')
    references = []
    
    try:
        bib_database = bibtexparser.loads(text)
        
        for entry in bib_database.entries:
            authors = entry.get('author', 'Unknown Authors')
            title = entry.get('title', 'Untitled')
            year = entry.get('year', '')
            journal = entry.get('journal', entry.get('booktitle', 'Unknown Source'))
            volume = entry.get('volume', '')
            number = entry.get('number', '')
            pages = entry.get('pages', '')
            doi = entry.get('doi', '')
            
            # สร้างรูปแบบข้อความสำหรับอ้างอิง
            ref = f"{authors}. ({year}). {title}. {journal}"
            
            if volume:
                ref += f", Vol. {volume}"
            if number:
                ref += f"({number})"
            if pages:
                ref += f", pp. {pages}"
            if doi:
                ref += f". doi: {doi}"
            
            references.append(ref)
        
        return references
    
    except Exception as e:
        logging.error(f"Error parsing BibTeX: {str(e)}")
        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์ BibTeX: {str(e)}")
        return []

# ฟังก์ชันนำเข้า RIS (EndNote)
def import_ris(ris_file):
    text = ris_file.read().decode('utf-8')
    references = []
    
    # แบ่งเป็นรายการอ้างอิงแต่ละรายการ
    entries = text.split('\nER  - \n')
    
    for entry in entries:
        if not entry.strip():
            continue
        
        lines = entry.strip().split('\n')
        entry_data = {}
        
        for line in lines:
            if not line or '  - ' not in line:
                continue
            
            tag, value = line.split('  - ', 1)
            tag = tag.strip()
            value = value.strip()
            
            if tag in entry_data:
                if isinstance(entry_data[tag], list):
                    entry_data[tag].append(value)
                else:
                    entry_data[tag] = [entry_data[tag], value]
            else:
                entry_data[tag] = value
        
        # รวบรวมข้อมูลผู้แต่ง
        authors = []
        for tag in ['AU', 'A1', 'A2', 'A3', 'A4']:
            if tag in entry_data:
                if isinstance(entry_data[tag], list):
                    authors.extend(entry_data[tag])
                else:
                    authors.append(entry_data[tag])
        
        authors_str = ', '.join(authors) if authors else 'Unknown Authors'
        
        # ข้อมูลอื่นๆ
        title = entry_data.get('TI', entry_data.get('T1', 'Untitled'))
        year = entry_data.get('PY', entry_data.get('Y1', ''))
        if year and len(year) >= 4:
            year = year[:4]
        
        journal = entry_data.get('JO', entry_data.get('T2', entry_data.get('JA', 'Unknown Source')))
        volume = entry_data.get('VL', '')
        issue = entry_data.get('IS', '')
        pages = entry_data.get('SP', '')
        
        if 'EP' in entry_data and pages:
            pages = f"{pages}-{entry_data['EP']}"
        
        doi = entry_data.get('DO', '')
        
        # สร้างรูปแบบข้อความสำหรับอ้างอิง
        ref = f"{authors_str}. ({year}). {title}. {journal}"
        
        if volume:
            ref += f", Vol. {volume}"
        if issue:
            ref += f"({issue})"
        if pages:
            ref += f", pp. {pages}"
        if doi:
            ref += f". doi: {doi}"
        
        references.append(ref)
    
    return references

# ฟังก์ชันส่งออกเป็น BibTeX
def export_to_bibtex(references):
    bibtex_output = ""
    
    for i, ref in enumerate(references):
        # สร้าง entry key
        key = f"ref{i+1}"
        
        # แยกข้อมูลจาก reference
        authors = extract_authors(ref)
        title = extract_title(ref)
        year = extract_year(ref)
        journal = extract_journal(ref)
        doi = extract_doi(ref)
        
        # แปลงชื่อผู้แต่งให้เป็นรูปแบบที่ถูกต้อง
        if "Unknown Authors" not in authors:
            authors = authors.replace(" and ", " AND ")
        
        # เริ่มสร้าง entry
        bibtex_output += f"@article{{{key},\n"
        bibtex_output += f"  author = {{{authors}}},\n"
        bibtex_output += f"  title = {{{title}}},\n"
        
        if year:
            bibtex_output += f"  year = {{{year}}},\n"
        
        if "Unknown Journal" not in journal:
            bibtex_output += f"  journal = {{{journal}}},\n"
        
        if doi:
            bibtex_output += f"  doi = {{{doi}}},\n"
        
        # ปิด entry
        bibtex_output += "}\n\n"
    
    return bibtex_output

# ฟังก์ชันสร้างกราฟแบบ star
def create_reference_graph(central_node, all_references, doi_references):
    progress_bar = st.session_state.progress_bar.progress(0, text=f"{get_ui_text('loading')} - เริ่มสร้างกราฟ")
    
    G = nx.DiGraph()
    
    # เตรียมชื่อโหนด (ตัดให้สั้นลงถ้ายาวเกินไป)
    central_label = central_node[:50] + ("..." if len(central_node) > 50 else "")
    G.add_node(central_label, color="red", size=30, title=central_node)
    
    total_refs = len(all_references)
    for i, ref in enumerate(all_references):
        # กำหนดสี
        if "doi:" in ref.lower() or ref.lower().startswith("http"):
            color = "skyblue"
        else:
            color = "gray"
        
        # เตรียมชื่อโหนด
        label = ref[:50] + ("..." if len(ref) > 50 else "")
        
        # เพิ่มโหนดและเส้นเชื่อม
        G.add_node(label, color=color, size=20, title=ref)
        G.add_edge(central_label, label)
        
        # อัปเดตแถบความคืบหน้า
        progress = (i + 1) / total_refs
        progress_bar.progress(progress, text=f"{get_ui_text('loading')} - เพิ่มโหนด {i+1}/{total_refs}")
        if i % 10 == 0:  # ลดความถี่ในการอัปเดต UI
            time.sleep(0.01)
    
    # สร้างกราฟแบบ pyvis
    net = Network(height="500px", width="100%", directed=True, notebook=False)
    net.from_nx(G)
    
    # ตั้งค่าการแสดงผล
    net.set_options("""
    var options = {
      "nodes": {
        "shape": "dot",
        "font": {
          "size": 12,
          "face": "tahoma"
        },
        "color": {
          "highlight": "#FF0000",
          "hover": "#FF9999"
        }
      },
      "edges": {
        "arrows": "to",
        "smooth": {
          "type": "continuous",
          "forceDirection": "none",
          "roundness": 0.2
        }
      },
      "physics": {
        "hierarchicalRepulsion": {
          "centralGravity": 0.0,
          "springLength": 150,
          "springConstant": 0.01,
          "nodeDistance": 120,
          "damping": 0.09
        },
        "solver": "hierarchicalRepulsion"
      },
      "interaction": {
        "navigationButtons": true,
        "keyboard": true
      }
    }
    """)
    
    # บันทึกกราฟ
    net.save_graph("graph.html")
    with open("graph.html", "r", encoding="utf-8") as f:
        graph_html = f.read()
    
    progress_bar.progress(1.0, text=f"{get_ui_text('loading')} - สร้างกราฟสำเร็จ")
    time.sleep(0.1)
    progress_bar.empty()
    
    return graph_html

# ฟังก์ชันส่งออกกราฟเป็น PDF
def export_graph_to_pdf(central_node, all_references):
    progress_bar = st.session_state.progress_bar.progress(0, text=f"{get_ui_text('loading')} - เริ่มส่งออกกราฟเป็น PDF")
    
    # สร้างกราฟ NetworkX
    G = nx.DiGraph()
    
    central_label = central_node[:30] + ("..." if len(central_node) > 30 else "")
    G.add_node(central_label, color="red")
    
    ref_nodes = []
    for ref in all_references:
        # จำกัดจำนวนโหนดสำหรับการส่งออก PDF เพื่อความสวยงาม
        if len(ref_nodes) >= 20:
            ref_nodes.append("...")
            break
            
        color = "skyblue" if "doi:" in ref.lower() or ref.lower().startswith("http") else "gray"
        label = ref[:30] + ("..." if len(ref) > 30 else "")
        G.add_node(label, color=color)
        G.add_edge(central_label, label)
        ref_nodes.append(label)
    
    # สร้าง PDF
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, k=0.3, iterations=50)
    
    # เตรียมรายการสี
    node_colors = [G.nodes[n].get('color', 'gray') for n in G.nodes()]
    
    # วาดโหนดและเส้นเชื่อม
    nx.draw(G, pos, with_labels=True, node_color=node_colors, 
            node_size=500, font_size=8, arrows=True, 
            arrowsize=15, width=1.5, alpha=0.8,
            font_weight='bold', font_family='sans-serif')
    
    plt.title(f"{get_ui_text('graph_title')} ({central_label})")
    
    # บันทึกเป็น PDF
    pdf_buffer = BytesIO()
    with PdfPages(pdf_buffer) as pdf:
        pdf.savefig(bbox_inches='tight')
    plt.close()
    
    progress_bar.progress(1.0, text=f"{get_ui_text('loading')} - ส่งออก PDF สำเร็จ")
    time.sleep(0.1)
    progress_bar.empty()
    
    pdf_buffer.seek(0)
    return pdf_buffer

# ฟังก์ชันสร้าง word cloud
def create_wordcloud(references):
    # รวมข้อความทั้งหมด
    text = " ".join(references)
    
    # ลบคำที่ไม่ต้องการ
    text = re.sub(r'\b\d+\b', '', text)  # ลบตัวเลข
    text = re.sub(r'http\S+|www\.\S+', '', text)  # ลบ URL
    text = re.sub(r'doi:\s*\S+', '', text)  # ลบ DOI
    
    # ลบเครื่องหมายวรรคตอนและแปลงเป็นตัวพิมพ์เล็ก
    text = re.sub(r'[^\w\s]', '', text).lower()
    
    # คำที่ไม่ต้องการในการวิเคราะห์
    stopwords = set([
        'the', 'and', 'of', 'in', 'on', 'for', 'with', 'to', 'a', 'an', 'by', 'is', 'are', 'was', 'were', 
        'that', 'this', 'these', 'those', 'it', 'as', 'at', 'be', 'from', 'has', 'have', 'had', 
        'doi', 'vol', 'volume', 'issue', 'pp', 'page', 'pages', 'journal', 'conference', 'proceedings',
        'international', 'university', 'year', 'new', 'study', 'analysis'
    ])
    
    # สร้าง word cloud
    wordcloud = WordCloud(width=800, height=400, background_color='white',
                         stopwords=stopwords, max_words=100, 
                         collocations=False, colormap='viridis').generate(text)
    
    # บันทึกเป็นไฟล์รูปภาพ
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    
    # บันทึกเป็นไฟล์รูปภาพ
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight')
    plt.close()
    
    img_buffer.seek(0)
    return img_buffer

# ฟังก์ชันเปรียบเทียบเอกสาร
def compare_documents(doc1_refs, doc2_refs):
    # แปลงเป็นเซต
    ref_set1 = set([ref.lower() for ref in doc1_refs])
    ref_set2 = set([ref.lower() for ref in doc2_refs])
    
    # หาอ้างอิงที่ใช้ร่วมกันและไม่ซ้ำกัน
    common_refs = ref_set1.intersection(ref_set2)
    unique_doc1 = ref_set1 - ref_set2
    unique_doc2 = ref_set2 - ref_set1
    
    # คำนวณค่าสถิติ
    total_doc1 = len(doc1_refs)
    total_doc2 = len(doc2_refs)
    total_common = len(common_refs)
    
    # คำนวณค่า Jaccard similarity
    jaccard = total_common / (total_doc1 + total_doc2 - total_common) if (total_doc1 + total_doc2 - total_common) > 0 else 0
    
    # เตรียมผลลัพธ์
    result = {
        "common": list(common_refs),
        "unique_doc1": list(unique_doc1),
        "unique_doc2": list(unique_doc2),
        "total_doc1": total_doc1,
        "total_doc2": total_doc2,
        "total_common": total_common,
        "jaccard_similarity": jaccard
    }
    
    return result

# ฟังก์ชันสร้าง dataframe จาก references
def create_references_dataframe(references):
    data = []
    
    for ref in references:
        data.append({
            "Reference": ref,
            "Authors": extract_authors(ref),
            "Title": extract_title(ref),
            "Year": extract_year(ref),
            "Journal": extract_journal(ref),
            "DOI": extract_doi(ref),
            "Publisher": extract_publisher(extract_doi(ref))
        })
    
    return pd.DataFrame(data)

# อินเตอร์เฟซ Streamlit
st.title(get_ui_text("title"))

# สร้างแท็บ
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📄 " + get_ui_text("references_list"), 
    "📊 " + get_ui_text("references_viz"), 
    "👥 " + get_ui_text("author_network"), 
    "🔄 " + get_ui_text("compare_documents"),
    "⚙️ " + get_ui_text("settings")
])

# แท็บการตั้งค่า
with tab5:
    st.header(get_ui_text("settings"))
    
    # เลือกภาษา
    language = st.selectbox(
        get_ui_text("language_setting"),
        options=["th", "en"],
        format_func=lambda x: "ไทย" if x == "th" else "English",
        index=0 if st.session_state.language == "th" else 1
    )
    
    if language != st.session_state.language:
        st.session_state.language = language
        st.experimental_rerun()
    
    # ปุ่มล้างแคช
    if st.button(get_ui_text("cache_setting")):
        result = clear_cache()
        st.success(result)
    
    # ปุ่ม Clear PDF
    if st.button(get_ui_text("clear_button")):
        st.session_state.current_doc = None
        st.session_state.references = []
        st.session_state.doi_references = []
        st.session_state.graph_html = None
        st.session_state.doc_history = {}
        st.session_state.author_network = None
        st.session_state.keyword_data = None
        st.success("ล้างข้อมูลเรียบร้อยแล้ว")

# แท็บ 1: รายการอ้างอิง
with tab1:
    # เลือกวิธีนำเข้า
    import_method = st.radio(
        get_ui_text("import_method"),
        options=["pdf", "bibtex", "ris", "doi"],
        format_func=lambda x: "PDF" if x == "pdf" else 
                         "BibTeX" if x == "bibtex" else
                         "RIS (EndNote)" if x == "ris" else "DOI",
        horizontal=True
    )
    
    if import_method == "pdf":
        uploaded_file = st.file_uploader(get_ui_text("upload_prompt"), type="pdf")
        
        # เมื่ออัปโหลดไฟล์ PDF ใหม่
        if uploaded_file is not None:
            st.session_state.progress_bar = st.empty()
            progress_bar = st.session_state.progress_bar.progress(0, text=f"{get_ui_text('loading')} - เริ่มประมวลผล PDF")
            
            time.sleep(0.5)  # จำลองการเริ่มต้น
            references = extract_references_from_pdf(uploaded_file)
            
            if references:
                st.session_state.current_doc = uploaded_file.name
                st.session_state.references = references
                st.session_state.doi_references = [ref for ref in references if "doi:" in ref.lower() or ref.lower().startswith("http")]
                st.session_state.graph_html = create_reference_graph(uploaded_file.name, st.session_state.references, st.session_state.doi_references)
                st.session_state.doc_history[uploaded_file.name] = {
                    "references": references,
                    "doi_references": st.session_state.doi_references
                }
                
                # วิเคราะห์เครือข่ายผู้แต่ง
                st.session_state.author_network = analyze_author_network(references)
                
                # วิเคราะห์คำสำคัญ
                st.session_state.keyword_data = analyze_keyword_frequency(references)
                
                st.success(f"พบ {len(references)} รายการอ้างอิง")
            else:
                st.warning("ไม่พบรายการอ้างอิงในเอกสาร กรุณาตรวจสอบไฟล์")
            
            st.session_state.progress_bar.empty()
    
    elif import_method == "bibtex":
        uploaded_bibtex = st.file_uploader(get_ui_text("upload_prompt_bibtex"), type=["bib", "bibtex", "txt"])
        
        if uploaded_bibtex is not None:
            st.session_state.progress_bar = st.empty()
            progress_bar = st.session_state.progress_bar.progress(0, text=f"{get_ui_text('loading')} - กำลังอ่านไฟล์ BibTeX")
            
            references = import_bibtex(uploaded_bibtex)
            
            if references:
                st.session_state.current_doc = uploaded_bibtex.name
                st.session_state.references = references
                st.session_state.doi_references = [ref for ref in references if "doi:" in ref.lower() or ref.lower().startswith("http")]
                st.session_state.graph_html = create_reference_graph(uploaded_bibtex.name, st.session_state.references, st.session_state.doi_references)
                st.session_state.doc_history[uploaded_bibtex.name] = {
                    "references": references,
                    "doi_references": st.session_state.doi_references
                }
                
                # วิเคราะห์เครือข่ายผู้แต่ง
                st.session_state.author_network = analyze_author_network(references)
                
                # วิเคราะห์คำสำคัญ
                st.session_state.keyword_data = analyze_keyword_frequency(references)
                
                st.success(f"นำเข้า {len(references)} รายการอ้างอิงจาก BibTeX สำเร็จ")
            else:
                st.warning("ไม่พบรายการอ้างอิงในไฟล์ BibTeX หรือไฟล์อาจไม่ถูกต้อง")
            
            st.session_state.progress_bar.empty()
    
    elif import_method == "ris":
        uploaded_ris = st.file_uploader(get_ui_text("upload_prompt_ris"), type=["ris", "txt"])
        
        if uploaded_ris is not None:
            st.session_state.progress_bar = st.empty()
            progress_bar = st.session_state.progress_bar.progress(0, text=f"{get_ui_text('loading')} - กำลังอ่านไฟล์ RIS")
            
            references = import_ris(uploaded_ris)
            
            if references:
                st.session_state.current_doc = uploaded_ris.name
                st.session_state.references = references
                st.session_state.doi_references = [ref for ref in references if "doi:" in ref.lower() or ref.lower().startswith("http")]
                st.session_state.graph_html = create_reference_graph(uploaded_ris.name, st.session_state.references, st.session_state.doi_references)
                st.session_state.doc_history[uploaded_ris.name] = {
                    "references": references,
                    "doi_references": st.session_state.doi_references
                }
                
                # วิเคราะห์เครือข่ายผู้แต่ง
                st.session_state.author_network = analyze_author_network(references)
                
                # วิเคราะห์คำสำคัญ
                st.session_state.keyword_data = analyze_keyword_frequency(references)
                
                st.success(f"นำเข้า {len(references)} รายการอ้างอิงจาก RIS สำเร็จ")
            else:
                st.warning("ไม่พบรายการอ้างอิงในไฟล์ RIS หรือไฟล์อาจไม่ถูกต้อง")
            
            st.session_state.progress_bar.empty()
            
    elif import_method == "doi":
        doi_input = st.text_input(get_ui_text("enter_doi"), value="10.")
        if st.button(get_ui_text("import")):
            if doi_inputและdoi_input.startswith("10."):
                st.session_state.progress_bar = st.empty()
                
                # ดาวน์โหลดจาก DOI
                url = f"https://doi.org/{doi_input}"
                pdf_content, message = cached_download_content(url)
                
                if pdf_content:
                    pdf_file = BytesIO(pdf_content)
                    references = extract_references_from_pdf(pdf_file)
                    
                    if references:
                        st.session_state.current_doc = doi_input
                        st.session_state.references = references
                        st.session_state.doi_references = [ref for ref in references if "doi:" in ref.lower() or ref.lower().startswith("http")]
                        st.session_state.graph_html = create_reference_graph(doi_input, st.session_state.references, st.session_state.doi_references)
                        st.session_state.doc_history[doi_input] = {
                            "references": references,
                            "doi_references": st.session_state.doi_references
                        }
                        
                        # วิเคราะห์เครือข่ายผู้แต่ง
                        st.session_state.author_network = analyze_author_network(references)
                        
                        # วิเคราะห์คำสำคัญ
                        st.session_state.keyword_data = analyze_keyword_frequency(references)
                        
                        st.success(f"ดาวน์โหลดและวิเคราะห์ DOI สำเร็จ พบ {len(references)} รายการอ้างอิง")
                    else:
                        st.warning("ดาวน์โหลดเอกสารสำเร็จแต่ไม่พบรายการอ้างอิง")
                else:
                    st.error(f"ไม่สามารถดาวน์โหลดเอกสารจาก DOI: {message}")
                
                st.session_state.progress_bar.empty()
            else:
                st.error("กรุณาป้อน DOI ที่ถูกต้อง ควรขึ้นต้นด้วย 10.")
    
    # แสดงผล references
    if st.session_state.references:
        st.subheader(get_ui_text("references_list"))
        
        # สร้าง DataFrame และแสดงเป็นตาราง
        df_refs = create_references_dataframe(st.session_state.references)
        
        # ปุ่มส่งออก
        col1, col2 = st.columns(2)
        with col1:
            if st.button(get_ui_text("export_csv")):
                csv = df_refs.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"references_{st.session_state.current_doc[:20]}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button(get_ui_text("export_bibtex")):
                bibtex = export_to_bibtex(st.session_state.references)
                st.download_button(
                    label="Download BibTeX",
                    data=bibtex,
                    file_name=f"references_{st.session_state.current_doc[:20]}.bib",
                    mime="text/plain"
                )
        
        # กลุ่ม 1: แสดงลิงก์ (URL) ด้านบน
        url_references = [ref for ref in st.session_state.references if ref.lower().startswith("http")]
        if url_references:
            st.subheader(get_ui_text("urls_section"))
            for i, ref in enumerate(url_references):
                with st.expander(f"URL {i+1}: {ref[:100]}..."):
                    st.write(f"Full: {ref}")
                    color = "green"
                    st.markdown(f'<p style="color:{color}">{ref}</p>', unsafe_allow_html=True)
                    ref_url = ref
                    if st.button(f"{get_ui_text('download_analyze')} - URL {i+1}", key=f"download_url_{i}"):
                        pdf_content, content = cached_download_content(ref_url)
                        if pdf_content:
                            pdf_file = BytesIO(pdf_content)
                            new_references = extract_references_from_pdf(pdf_file)
                            # แสดง references ของเอกสารที่ดาวน์โหลด
                            st.subheader(f"References from {ref_url}")
                            for j, new_ref in enumerate(new_references):
                                with st.expander(f"Sub-reference {j+1}: {new_ref[:100]}..."):
                                    st.write(f"Full: {new_ref}")
                                    color = "green" if "doi:" in new_ref.lower() or new_ref.lower().startswith("http") else "gray"
                                    st.markdown(f'<p style="color:{color}">{new_ref}</p>', unsafe_allow_html=True)
                            # อัปเดตสถานะ
                            st.session_state.current_doc = ref_url
                            st.session_state.references = new_references
                            st.session_state.doi_references = [r for r in new_references if "doi:" in r.lower() or r.lower().startswith("http")]
                            st.session_state.graph_html = create_reference_graph(ref_url, st.session_state.references, st.session_state.doi_references)
                            st.session_state.doc_history[ref_url] = {
                                "references": new_references,
                                "doi_references": st.session_state.doi_references
                            }
                            st.success(get_ui_text("download_success"))
                        else:
                            st.error(content)
        
        # กลุ่ม 2: แสดงอ้างอิงทั่วไป (รวมที่มี DOI) ด้านล่าง
        other_references = [ref for ref in st.session_state.references if not ref.lower().startswith("http")]
        if other_references:
            st.subheader(get_ui_text("general_references"))
            for i, ref in enumerate(other_references):
                # เตรียมข้อมูลสำหรับการแสดงผล
                doi = extract_doi(ref)
                authors = extract_authors(ref)
                year = extract_year(ref)
                title = extract_title(ref)
                journal = extract_journal(ref)
                
                # สร้างหัวข้อที่กระชับกว่า
                header_text = f"{authors[:30]}{'...' if len(authors) > 30 else ''} ({year if year else 'n/a'})"
                
                with st.expander(f"Ref {i+1}: {header_text}"):
                    st.markdown(f"**Full Reference:** {ref}")
                    st.markdown(f"**Authors:** {authors}")
                    st.markdown(f"**Title:** {title}")
                    st.markdown(f"**Year:** {year if year else 'Not found'}")
                    st.markdown(f"**Journal:** {journal}")
                    
                    if doi:
                        st.markdown(f"**DOI:** [{doi}](https://doi.org/{doi})")
                        st.markdown(f"**Publisher:** {extract_publisher(doi)}")
                        
                        ref_url = f"https://doi.org/{doi}"
                        if st.button(f"{get_ui_text('download_analyze')} - Ref {i+1}", key=f"download_ref_{i}"):
                            pdf_content, content = cached_download_content(ref_url)
                            if pdf_content:
                                pdf_file = BytesIO(pdf_content)
                                new_references = extract_references_from_pdf(pdf_file)
                                # แสดง references ของเอกสารที่ดาวน์โหลด
                                if new_references:
                                    st.subheader(f"References from {ref_url}")
                                    for j, new_ref in enumerate(new_references[:5]):  # แสดงเพียง 5 รายการแรก
                                        st.markdown(f"**{j+1}.** {new_ref[:100]}...")
                                    
                                    if len(new_references) > 5:
                                        st.markdown(f"*...and {len(new_references) - 5} more references*")
                                    
                                    # อัปเดตสถานะ
                                    st.session_state.current_doc = ref_url
                                    st.session_state.references = new_references
                                    st.session_state.doi_references = [r for r in new_references if "doi:" in r.lower() or r.lower().startswith("http")]
                                    st.session_state.graph_html = create_reference_graph(ref_url, st.session_state.references, st.session_state.doi_references)
                                    st.session_state.doc_history[ref_url] = {
                                        "references": new_references,
                                        "doi_references": st.session_state.doi_references
                                    }
                                    
                                    # วิเคราะห์เครือข่ายผู้แต่ง
                                    st.session_state.author_network = analyze_author_network(new_references)
                                    
                                    # วิเคราะห์คำสำคัญ
                                    st.session_state.keyword_data = analyze_keyword_frequency(new_references)
                                    
                                    st.success(f"{get_ui_text('download_success')} - {len(new_references)} references found")
                                else:
                                    st.warning("ดาวน์โหลดสำเร็จแต่ไม่พบรายการอ้างอิง")
                            else:
                                st.error(content)
                    else:
                        st.markdown("**DOI:** Not found")
    else:
        st.write("กรุณาอัปโหลดไฟล์ PDF เพื่อเริ่มการวิเคราะห์")

# แท็บ 2: การวิเคราะห์แบบมีภาพ
with tab2:
    if st.session_state.references:
        # แสดงกราฟ
        st.subheader(f"{get_ui_text('graph_title')} ({st.session_state.current_doc})")
        if st.session_state.graph_html:
            html(st.session_state.graph_html, height=550, width=None)
            
            # ปุ่มส่งออก PDF
            pdf_buffer = export_graph_to_pdf(st.session_state.current_doc, st.session_state.references)
            st.download_button(
                label=get_ui_text("export_pdf"),
                data=pdf_buffer,
                file_name=f"graph_{st.session_state.current_doc[:20]}.pdf",
                mime="application/pdf"
            )
        
        # Visualization ด้วย Altair
        st.subheader(get_ui_text("insights_title"))
        
        # 1. กราฟแสดงการกระจายตัวของ References ตามปี
        years = [extract_year(ref) for ref in st.session_state.references if extract_year(ref)]
        if years:
            df_years = pd.DataFrame(years, columns=["Year"])
            chart_years = alt.Chart(df_years).mark_bar().encode(
                x=alt.X("Year:O", title=get_ui_text("publication_year")),
                y=alt.Y("count()", title=get_ui_text("references_count")),
                tooltip=["Year", "count()"]
            ).properties(
                title=get_ui_text("year_distribution"),
                width=600,
                height=400
            ).interactive()
            st.altair_chart(chart_years)
            
            # เพิ่มการวิเคราะห์แนวโน้มปี
            years_array = np.array(years)
            if len(years_array) > 0:
                st.write(f"**ปีเฉลี่ย (Mean):** {np.mean(years_array):.2f}")
                st.write(f"**ปีที่มีการอ้างอิงมากที่สุด:** {pd.Series(years).value_counts().index[0]}")
                st.write(f"**ช่วงปี:** {min(years)} - {max(years)}")
                
                # วิเคราะห์อายุของการอ้างอิง
                current_year = 2025  # ปัจจุบัน
                ref_ages = current_year - np.array(years)
                st.write(f"**อายุการอ้างอิงเฉลี่ย:** {np.mean(ref_ages):.2f} ปี")
        else:
            st.write(get_ui_text("no_data"))
        
        # 2. กราฟแสดงจำนวน References ตามสำนักพิมพ์
        publishers = []
        for ref in st.session_state.references:
            doi = extract_doi(ref)
            publisher = extract_publisher(doi) if doi else "Unknown"
            publishers.append(publisher)
        df_publishers = pd.DataFrame(publishers, columns=["Publisher"])
        if not df_publishers.empty:
            # ดึงเฉพาะสำนักพิมพ์ที่พบบ่อย
            publisher_counts = df_publishers['Publisher'].value_counts()
            top_publishers = publisher_counts[publisher_counts >= 2].index.tolist()
            
            # รวมสำนักพิมพ์ที่พบน้อยเป็น "Others"
            df_publishers['Publisher'] = df_publishers['Publisher'].apply(
                lambda x: x if x in top_publishers else "Others")
            
            chart_publishers = alt.Chart(df_publishers).mark_bar().encode(
                x=alt.X("count()", title=get_ui_text("references_count")),
                y=alt.Y("Publisher", title=get_ui_text("publisher"), sort='-x'),
                color="Publisher",
                tooltip=["Publisher", "count()"]
            ).properties(
                title=get_ui_text("publisher_distribution"),
                width=600,
                height=400
            ).interactive()
            st.altair_chart(chart_publishers)
        else:
            st.write(get_ui_text("no_data"))
        
        # 3. Word Cloud ของคำสำคัญ
        st.subheader(get_ui_text("wordcloud"))
        wordcloud_img = create_wordcloud(st.session_state.references)
        st.image(wordcloud_img)
        
        # 4. แสดงคำสำคัญที่พบบ่อย
        if st.session_state.keyword_data:
            st.subheader(get_ui_text("top_keywords"))
            
            # สร้าง DataFrame จากข้อมูลคำสำคัญ
            df_keywords = pd.DataFrame(st.session_state.keyword_data, columns=["Keyword", "Count"])
            
            # แสดงกราฟ
            chart_keywords = alt.Chart(df_keywords.head(15)).mark_bar().encode(
                x=alt.X("Count:Q", title="จำนวนครั้งที่พบ"),
                y=alt.Y("Keyword:N", title="คำสำคัญ", sort='-x'),
                color=alt.Color("Count:Q", scale=alt.Scale(scheme='blues')),
                tooltip=["Keyword", "Count"]
            ).properties(
                title="คำสำคัญยอดนิยม 15 อันดับแรก",
                width=600,
                height=400
            ).interactive()
            st.altair_chart(chart_keywords)
    else:
        st.write("กรุณาอัปโหลดไฟล์ PDF เพื่อเริ่มการวิเคราะห์")

# แท็บ 3: เครือข่ายผู้แต่ง
with tab3:
    if st.session_state.author_network and st.session_state.author_network.number_of_nodes() > 0:
        st.subheader(get_ui_text("author_network"))
        
        # สร้างกราฟเครือข่ายผู้แต่ง
        author_graph_html = create_author_network_graph(st.session_state.author_network)
        
        if author_graph_html:
            html(author_graph_html, height=550, width=None)
            
            # แสดงข้อมูลสถิติเกี่ยวกับเครือข่ายผู้แต่ง
            st.subheader("ข้อมูลสถิติเครือข่ายผู้แต่ง")
            
            # จำนวนผู้แต่งทั้งหมด
            total_authors = st.session_state.author_network.number_of_nodes()
            st.write(f"**จำนวนผู้แต่งทั้งหมด:** {total_authors}")
            
            # จำนวนความร่วมมือ
            total_collaborations = st.session_state.author_network.number_of_edges()
            st.write(f"**จำนวนความร่วมมือทั้งหมด:** {total_collaborations}")
            
            # ผู้แต่งที่มีความร่วมมือมากที่สุด
            if total_authors > 0:
                top_collaborators = sorted(st.session_state.author_network.degree, key=lambda x: x[1], reverse=True)
                
                if top_collaborators:
                    st.write("### ผู้แต่งที่มีความร่วมมือมากที่สุด (Top Collaborators)")
                    top_5 = top_collaborators[:min(5, len(top_collaborators))]
                    
                    # สร้าง DataFrame
                    df_top_authors = pd.DataFrame([
                        {"ผู้แต่ง": author, "จำนวนความร่วมมือ": degree}
                        for author, degree in top_5
                    ])
                    
                    st.dataframe(df_top_authors)
        else:
            st.write("ไม่สามารถสร้างกราฟเครือข่ายผู้แต่งได้")
    else:
        st.write("ไม่พบข้อมูลผู้แต่งที่เพียงพอสำหรับการวิเคราะห์เครือข่าย")

# แท็บ 4: เปรียบเทียบเอกสาร
with tab4:
    st.subheader(get_ui_text("compare_documents"))
    
    if len(st.session_state.doc_history) >= 2:
        doc_names = list(st.session_state.doc_history.keys())
        
        col1, col2 = st.columns(2)
        
        with col1:
            doc1 = st.selectbox("เอกสารที่ 1", options=doc_names, index=0)
        
        with col2:
            doc2 = st.selectbox("เอกสารที่ 2", options=doc_names, index=min(1, len(doc_names)-1))
        
        if doc1 != doc2:
            doc1_refs = st.session_state.doc_history[doc1]["references"]
            doc2_refs = st.session_state.doc_history[doc2]["references"]
            
            if st.button("เปรียบเทียบเอกสาร"):
                st.session_state.progress_bar = st.empty()
                progress_bar = st.session_state.progress_bar.progress(0, text="กำลังเปรียบเทียบเอกสาร...")
                
                # ดำเนินการเปรียบเทียบ
                comparison_result = compare_documents(doc1_refs, doc2_refs)
                
                progress_bar.progress(1.0, text="เปรียบเทียบเสร็จสิ้น")
                time.sleep(0.5)
                st.session_state.progress_bar.empty()
                
                # แสดงผลลัพธ์
                st.subheader("ผลการเปรียบเทียบ")
                
                # แสดงค่าความคล้ายคลึง
                sim_percent = comparison_result["jaccard_similarity"] * 100
                st.metric("ความคล้ายคลึงของรายการอ้างอิง (Jaccard Similarity)", f"{sim_percent:.2f}%")
                
                # แสดงข้อมูลสถิติ
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("จำนวนอ้างอิงในเอกสารที่ 1", comparison_result["total_doc1"])
                with col2:
                    st.metric("จำนวนอ้างอิงในเอกสารที่ 2", comparison_result["total_doc2"])
                with col3:
                    st.metric("จำนวนอ้างอิงที่ใช้ร่วมกัน", comparison_result["total_common"])
                
                # แสดงรายการอ้างอิงที่ใช้ร่วมกัน
                if comparison_result["common"]:
                    with st.expander(f"{get_ui_text('common_references')} ({len(comparison_result['common'])})", expanded=True):
                        for i, ref in enumerate(comparison_result["common"]):
                            st.markdown(f"**{i+1}.** {ref}")
                else:
                    st.info("ไม่พบรายการอ้างอิงที่ใช้ร่วมกัน")
                
                # แสดงรายการอ้างอิงที่พบเฉพาะในเอกสารที่ 1
                if comparison_result["unique_doc1"]:
                    with st.expander(f"อ้างอิงเฉพาะในเอกสารที่ 1: {doc1} ({len(comparison_result['unique_doc1'])})", expanded=False):
                        for i, ref in enumerate(comparison_result["unique_doc1"]):
                            st.markdown(f"**{i+1}.** {ref}")
                
                # แสดงรายการอ้างอิงที่พบเฉพาะในเอกสารที่ 2
                if comparison_result["unique_doc2"]:
                    with st.expander(f"อ้างอิงเฉพาะในเอกสารที่ 2: {doc2} ({len(comparison_result['unique_doc2'])})", expanded=False):
                        for i, ref in enumerate(comparison_result["unique_doc2"]):
                            st.markdown(f"**{i+1}.** {ref}")
        else:
            st.warning("กรุณาเลือกเอกสารที่แตกต่างกันสำหรับการเปรียบเทียบ")
    else:
        st.info("คุณต้องวิเคราะห์อย่างน้อย 2 เอกสารเพื่อใช้ฟีเจอร์การเปรียบเทียบ")

st.write("---")
st.write("วันที่ปรับปรุงล่าสุด: 9 มีนาคม 2568")
st.write("ผู้พัฒนา: อนุสรณ์ ใจแก้ว")

st.write("---")
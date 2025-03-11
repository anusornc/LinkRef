# โปรแกรมวิเคราะห์เอกสารอ้างอิง

โปรเจกต์นี้เป็นโปรแกรมวิเคราะห์เอกสารอ้างอิงที่ช่วยให้คุณวิเคราะห์เอกสารอ้างอิงจากไฟล์ PDF, ไฟล์ BibTeX, ไฟล์ RIS และ DOI โดยมีฟีเจอร์การแสดงผลภาพ, เครือข่ายผู้แต่ง, การวิเคราะห์คำสำคัญ และการเปรียบเทียบเอกสาร

## ข้อกำหนด

ตรวจสอบให้แน่ใจว่าคุณได้ติดตั้งไลบรารีต่อไปนี้:

- Python 3.7+
- Streamlit
- PyPDF2
- Requests
- Pyvis
- Networkx
- Matplotlib
- Altair
- Pandas
- BeautifulSoup4
- Bibtexparser
- Wordcloud
- Numpy
- Unidecode
- Urllib3

คุณสามารถติดตั้งแพ็กเกจที่ต้องการได้โดยใช้คำสั่งต่อไปนี้:

```sh
pip install -r requirements.txt
```

## วิธีการรัน

1. โคลนโปรเจกต์จาก repository:

```sh
git clone https://github.com/yourusername/LinkRef.git
cd LinkRef
```

2. ติดตั้งไลบรารีที่ต้องการ:

```sh
pip install -r requirements.txt
```

3. รันแอปพลิเคชัน Streamlit:

```sh
streamlit run linkref.py
```

4. เปิดเว็บเบราว์เซอร์ของคุณและไปที่ `http://localhost:8501` เพื่อเข้าใช้งานแอปพลิเคชัน

## ฟีเจอร์
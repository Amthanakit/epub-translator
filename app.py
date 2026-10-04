import tempfile
import time
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import ebooklib
from ebooklib import epub
import streamlit as st

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="Eva01 Style - EPUB Translator", page_icon="📖", layout="centered"
)

# ส่วนหัวของแอปพลิเคชัน
st.title("📖 เครื่องมือแปลหนังสือ EPUB (อังกฤษ ➡️️ ไทย)")
st.write(
    "อัปโหลดไฟล์หนังสือของคุณ เลือกรูปแบบการแปลที่ต้องการ ระบบจะทำการแปลให้อัตโนมัติ"
)

# สร้างกล่องเลือก Option ตามที่คุณต้องการ
st.markdown("### ⚙️ ตั้งค่ารูปแบบการแปล")
translation_mode = st.radio(
    "เลือกโหมดการแปลภาษา:",
    (
        "📚 แบบสองภาษา (สลับย่อหน้า: ต้นฉบับอังกฤษบน - แปลไทยล่าง)",
        "🇹🇭 เฉพาะภาษาไทยล้วน (แปลธรรมชาติ อ่านลื่นไหล)",
    ),
)

# ช่องอัปโหลดไฟล์
uploaded_file = st.file_uploader(
    "เลือกไฟล์หนังสือรูปแบบ .epub", type=["epub"]
)


def translate_text(text, mode_bilingual=True):
  if not text.strip() or len(text.strip()) < 3:
    return text
  try:
    translator = GoogleTranslator(source="en", target="th")
    # ตัดแบ่งข้อความหากยาวเกินโควต้าของ Google Translate
    if len(text) > 4000:
      chunks = [text[i : i + 4000] for i in range(0, len(text), 4000)]
      translated_chunks = [translator.translate(chunk) for chunk in chunks]
      translated_text = "".join(translated_chunks)
    else:
      translated_text = translator.translate(text)
    time.sleep(0.3)  # หน่วงเวลาเล็กน้อยเพื่อความเสถียร

    if mode_bilingual:
      return f"{text}\n\n{translated_text}"
    else:
      return translated_text
  except Exception as e:
    return text


if uploaded_file is not None:
  st.info(f"📁 ไฟล์ที่เลือก: **{uploaded_file.name}**")

  if st.button("🚀 เริ่มต้นแปลหนังสือเลย"):
    progress_bar = st.progress(0)
    status_text = st.empty()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp_in:
      tmp_in.write(uploaded_file.getbuffer())
      input_path = tmp_in.name

    output_path = input_path.replace(".epub", "_translated.epub")

    try:
      status_text.text("กำลังอ่านโครงสร้างไฟล์หนังสือ...")
      book = epub.read_epub(input_path)
      new_book = epub.EpubBook()

      # ป้องกัน Error กรณีหนังสือไม่มีรหัส Identifier
      try:
        book_id = book.identifier if book.identifier else "id123456"
      except Exception:
        book_id = "id123456"
      new_book.set_identifier(str(book_id))

      # ตั้งชื่อหนังสือและภาษา
      try:
        book_title = book.title if book.title else "Untitled Book"
      except Exception:
        book_title = "Untitled Book"

      is_bilingual = "แบบสองภาษา" in translation_mode
      new_book.set_title(
          book_title + (" (Bilingual)" if is_bilingual else " (Thai)")
      )
      new_book.set_language("th")

      # จัดการข้อมูลผู้แต่ง
      try:
        authors = book.get_authors()
        if authors:
          for author in authors:
            new_book.add_author(author)
        else:
          new_book.add_author("Unknown Author")
      except Exception:
        new_book.add_author("Unknown Author")

      status_text.text("กำลังแปลเนื้อหาภายในหนังสือ โปรดรอสักครู่...")

      # ดึงรายการเอกสารทั้งหมดมาประมวลผล
      items = list(book.get_items())
      total_items = len(items)

      for idx, item in enumerate(items):
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
          try:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            paragraphs = soup.find_all(["p", "h1", "h2", "h3", "h4"])
            for p in paragraphs:
              orig_text = p.get_text()
              if len(orig_text.strip()) > 2:
                translated = translate_text(
                    orig_text, mode_bilingual=is_bilingual
                )
                p.string = translated
            item.set_content(str(soup).encode("utf-8"))
          except Exception:
            pass
        new_book.add_item(item)

        # อัปเดตแถบสถานะความคืบหน้า
        progress = min((idx + 1) / total_items, 1.0)
        progress_bar.progress(progress)

      epub.write_epub(output_path, new_book)
      status_text.text("แปลหนังสือเสร็จสมบูรณ์!")
      st.success("🎉 แปลหนังสือเรียบร้อยแล้ว พร้อมดาวน์โหลดใช้งานได้ทันที!")

      # ปุ่มดาวน์โหลด
      with open(output_path, "rb") as f:
        st.download_button(
            label="📥 ดาวน์โหลดไฟล์ EPUB ที่แปลแล้ว",
            data=f,
            file_name=uploaded_file.name.replace(".epub", "_Thai.epub"),
            mime="application/epub+zip",
        )

    except Exception as e:
      st.error(
          f"เกิดข้อผิดพลาดขึ้นในกระบวนการแปล: {str(e)}"
      )

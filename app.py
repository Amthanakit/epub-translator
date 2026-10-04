import tempfile
import time
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import ebooklib
from ebooklib import epub
import streamlit as st

st.set_page_config(
    page_title="EPUB Book Translator", page_icon="📚", layout="centered"
)

st.title("📚 แปลหนังสือ EPUB (อังกฤษ ➡️ ไทย)")
st.write(
    "อัปโหลดไฟล์ EPUB เลือกรูปแบบการแปล แล้วกดแปลได้ทันที (ไม่ต้องใช้ API Key)"
)

translation_mode = st.radio(
    "เลือกรูปแบบการแปล:",
    (
        "สองภาษา (สลับย่อหน้า: อังกฤษบน - ไทยล่าง)",
        "ภาษาไทยล้วน (แปลธรรมชาติ อ่านง่าย)",
    ),
)

uploaded_file = st.file_uploader(
    "เลือกไฟล์หนังสือ EPUB ของคุณ", type=["epub"]
)


def translate_text(text, mode_bilingual=True):
  if not text.strip() or len(text.strip()) < 3:
    return text
  try:
    translator = GoogleTranslator(source="en", target="th")
    if len(text) > 4000:
      chunks = [text[i : i + 4000] for i in range(0, len(text), 4000)]
      translated_chunks = [translator.translate(chunk) for chunk in chunks]
      translated_text = "".join(translated_chunks)
    else:
      translated_text = translator.translate(text)
    time.sleep(0.3)

    if mode_bilingual:
      return f"{text}\n\n{translated_text}"
    else:
      return translated_text
  except Exception as e:
    return text


if uploaded_file is not None:
  if st.button("🚀 เริ่มต้นแปลหนังสือ"):
    with st.spinner("กำลังแปลหนังสือ โปรดรอสักครู่..."):
      with tempfile.NamedTemporaryFile(delete=False, suffix=".epub") as tmp_in:
        tmp_in.write(uploaded_file.getbuffer())
        input_path = tmp_in.name

      output_path = input_path.replace(".epub", "_translated.epub")

      book = epub.read_epub(input_path)
      new_book = epub.EpubBook()

      # --- ป้องกัน Error กรณีหนังสือไม่มี Identifier ---
      try:
        book_id = book.identifier
        if not book_id:
          book_id = "id123456"
      except Exception:
        book_id = "id123456"
      new_book.set_identifier(str(book_id))

      # --- ป้องกัน Error กรณีหนังสือไม่มี Title ---
      try:
        book_title = book.title if book.title else "Untitled Book"
      except Exception:
        book_title = "Untitled Book"

      is_bilingual = "สองภาษา" in translation_mode
      new_book.set_title(
          book_title + (" (Bilingual)" if is_bilingual else " (Thai)")
      )
      new_book.set_language("th")

      # --- ป้องกัน Error กรณีหนังสือไม่มี Authors ---
      try:
        authors = book.get_authors()
        if authors:
          for author in authors:
            new_book.add_author(author)
        else:
          new_book.add_author("Unknown Author")
      except Exception:
        new_book.add_author("Unknown Author")

      # ประมวลผลแต่ละบท
      for item in book.get_items():
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
            pass  # หากหน้าไหนแปลงพลาด ข้ามไปหน้าถัดไปทันที
        new_book.add_item(item)

      epub.write_epub(output_path, new_book)

    st.success("🎉 แปลหนังสือเสร็จเรียบร้อยแล้ว!")
    with open(output_path, "rb") as f:
      st.download_button(
          label="📥 ดาวน์โหลดไฟล์ EPUB ที่แปลแล้ว",
          data=f,
          file_name=uploaded_file.name.replace(".epub", "_Thai.epub"),
          mime="application/epub+zip",
      )
